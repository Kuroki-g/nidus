use std::path::Path;

use anyhow::{Context, Result};
use tokenizers::Tokenizer;

pub const VECTOR_SIZE: usize = 1024;

/// model2vec 推論エンジン。
///
/// `model_dir` に `tokenizer.json` と `model.safetensors` が存在することを前提とする。
pub struct EmbeddingModel {
    tokenizer: Tokenizer,
    /// 平坦化した重み行列: [vocab_size * VECTOR_SIZE] f32（row-major）
    weights: Vec<f32>,
    vocab_size: usize,
}

impl EmbeddingModel {
    /// `model_dir` からモデルをロードする。
    pub fn load(model_dir: &Path) -> Result<Self> {
        let tokenizer_path = model_dir.join("tokenizer.json");
        let model_path = model_dir.join("model.safetensors");

        let tokenizer = Tokenizer::from_file(&tokenizer_path)
            .map_err(|e| anyhow::anyhow!("tokenizer load failed: {e}"))?;

        let bytes = std::fs::read(&model_path)
            .with_context(|| format!("cannot read {}", model_path.display()))?;

        let tensors =
            safetensors::SafeTensors::deserialize(&bytes).context("safetensors parse failed")?;

        let tensor = tensors
            .tensor("embedding.weight")
            .context("embedding.weight not found")?;

        let shape = tensor.shape();
        anyhow::ensure!(shape.len() == 2, "unexpected tensor rank: {}", shape.len());
        anyhow::ensure!(
            shape[1] == VECTOR_SIZE,
            "unexpected embedding dim: {}",
            shape[1]
        );
        let vocab_size = shape[0];

        // &[u8] → Vec<f32>（little-endian）
        let weights: Vec<f32> = tensor
            .data()
            .chunks_exact(4)
            .map(|b| f32::from_le_bytes([b[0], b[1], b[2], b[3]]))
            .collect();

        Ok(Self {
            tokenizer,
            weights,
            vocab_size,
        })
    }

    /// テキストを 1024 次元の L2 正規化済みベクターに変換する。
    ///
    /// 推論アルゴリズム:
    /// 1. トークナイザでエンコード（特殊トークン込み）
    /// 2. 各トークン ID の埋め込み行を取得
    /// 3. 平均プーリング
    /// 4. L2 正規化
    pub fn embed(&self, text: &str) -> Vec<f32> {
        let encoding = match self.tokenizer.encode(text, true) {
            Ok(enc) => enc,
            Err(_) => return vec![0.0_f32; VECTOR_SIZE],
        };

        let ids = encoding.get_ids();
        if ids.is_empty() {
            return vec![0.0_f32; VECTOR_SIZE];
        }

        let mut sum = vec![0.0_f32; VECTOR_SIZE];
        let mut count = 0usize;

        for &id in ids {
            let idx = id as usize;
            if idx < self.vocab_size {
                let row = &self.weights[idx * VECTOR_SIZE..(idx + 1) * VECTOR_SIZE];
                for (s, &w) in sum.iter_mut().zip(row.iter()) {
                    *s += w;
                }
                count += 1;
            }
        }

        if count > 0 {
            let n = count as f32;
            for s in &mut sum {
                *s /= n;
            }
        }

        // L2 正規化
        let norm: f32 = sum.iter().map(|x| x * x).sum::<f32>().sqrt();
        if norm > 0.0 {
            for s in &mut sum {
                *s /= norm;
            }
        }

        sum
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// モデルファイルが存在する場合のみ実行する統合テスト。
    /// `cargo test -- --ignored` で明示的に実行する。
    #[test]
    #[ignore]
    fn test_embed_shape_and_norm() {
        let model_dir = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../../tmp_model_build/0_StaticEmbedding");

        let model = EmbeddingModel::load(&model_dir).expect("model load failed");

        let v = model.embed("こんにちは世界");
        assert_eq!(v.len(), VECTOR_SIZE);

        let norm: f32 = v.iter().map(|x| x * x).sum::<f32>().sqrt();
        assert!((norm - 1.0).abs() < 1e-5, "norm should be ~1.0, got {norm}");
    }

    #[test]
    #[ignore]
    fn test_embed_different_texts_differ() {
        let model_dir = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../../tmp_model_build/0_StaticEmbedding");

        let model = EmbeddingModel::load(&model_dir).expect("model load failed");

        let v1 = model.embed("こんにちは世界");
        let v2 = model.embed("機械学習");

        // コサイン類似度: v1 と v2 は異なるはず（いずれも正規化済み）
        let dot: f32 = v1.iter().zip(v2.iter()).map(|(a, b)| a * b).sum();
        assert!(dot < 0.99, "different texts should differ, cosine={dot}");
    }
}
