use anyhow::Result;
use parking_lot::RwLock;
use std::collections::HashMap;
use tracing::debug;

/// Simple BM25 index implementation for hybrid search
pub struct BM25Index {
    /// Document store: id -> (content, tokens)
    documents: RwLock<HashMap<String, (String, Vec<String>)>>,
    /// Document frequency for each term
    doc_freq: RwLock<HashMap<String, usize>>,
    /// Average document length
    avg_doc_len: RwLock<f32>,
    /// BM25 parameters
    k1: f32,
    b: f32,
}

impl Default for BM25Index {
    fn default() -> Self {
        Self::new()
    }
}

impl BM25Index {
    pub fn new() -> Self {
        Self {
            documents: RwLock::new(HashMap::new()),
            doc_freq: RwLock::new(HashMap::new()),
            avg_doc_len: RwLock::new(0.0),
            k1: 1.5,
            b: 0.75,
        }
    }

    pub fn with_params(k1: f32, b: f32) -> Self {
        Self {
            documents: RwLock::new(HashMap::new()),
            doc_freq: RwLock::new(HashMap::new()),
            avg_doc_len: RwLock::new(0.0),
            k1,
            b,
        }
    }

    /// Tokenize text into lowercase terms
    fn tokenize(text: &str) -> Vec<String> {
        text.to_lowercase()
            .split(|c: char| !c.is_alphanumeric())
            .filter(|s| !s.is_empty() && s.len() > 1)
            .map(|s| s.to_string())
            .collect()
    }

    /// Add a document to the index
    pub fn add_document(&self, id: &str, content: &str) {
        let tokens = Self::tokenize(content);

        // Update document frequency for unique terms
        let unique_terms: std::collections::HashSet<_> = tokens.iter().collect();
        {
            let mut doc_freq = self.doc_freq.write();
            for term in unique_terms {
                *doc_freq.entry(term.clone()).or_insert(0) += 1;
            }
        }

        // Store document
        {
            let mut docs = self.documents.write();
            docs.insert(id.to_string(), (content.to_string(), tokens));
        }

        // Update average document length
        self.update_avg_doc_len();
    }

    /// Add multiple documents to the index
    pub fn add_documents(&self, documents: &[(String, String)]) {
        for (id, content) in documents {
            self.add_document(id, content);
        }
    }

    /// Update average document length
    fn update_avg_doc_len(&self) {
        let docs = self.documents.read();
        if docs.is_empty() {
            *self.avg_doc_len.write() = 0.0;
            return;
        }

        let total_len: usize = docs.values().map(|(_, tokens)| tokens.len()).sum();
        *self.avg_doc_len.write() = total_len as f32 / docs.len() as f32;
    }

    /// Search the index and return ranked results
    pub fn search(&self, query: &str, top_k: usize) -> Vec<(String, f32)> {
        let query_tokens = Self::tokenize(query);
        if query_tokens.is_empty() {
            return vec![];
        }

        debug!("BM25 search for {} tokens", query_tokens.len());

        let docs = self.documents.read();
        let doc_freq = self.doc_freq.read();
        let avg_doc_len = *self.avg_doc_len.read();
        let n = docs.len() as f32;

        if docs.is_empty() {
            return vec![];
        }

        // Calculate BM25 scores for each document
        let mut scores: Vec<(String, f32)> = docs
            .iter()
            .map(|(id, (_, doc_tokens))| {
                let doc_len = doc_tokens.len() as f32;
                let mut score = 0.0;

                // Count term frequencies in document
                let mut term_freq: HashMap<&str, usize> = HashMap::new();
                for token in doc_tokens {
                    *term_freq.entry(token.as_str()).or_insert(0) += 1;
                }

                for query_term in &query_tokens {
                    let tf = *term_freq.get(query_term.as_str()).unwrap_or(&0) as f32;
                    let df = *doc_freq.get(query_term).unwrap_or(&0) as f32;

                    if tf > 0.0 && df > 0.0 {
                        // IDF component
                        let idf = ((n - df + 0.5) / (df + 0.5) + 1.0).ln();

                        // TF component with length normalization
                        let tf_norm = (tf * (self.k1 + 1.0))
                            / (tf + self.k1 * (1.0 - self.b + self.b * doc_len / avg_doc_len));

                        score += idf * tf_norm;
                    }
                }

                (id.clone(), score)
            })
            .filter(|(_, score)| *score > 0.0)
            .collect();

        // Sort by score descending
        scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

        // Return top_k results
        scores.truncate(top_k);
        scores
    }

    /// Get document content by ID
    pub fn get_document(&self, id: &str) -> Option<String> {
        self.documents.read().get(id).map(|(content, _)| content.clone())
    }

    /// Clear all documents from the index
    pub fn clear(&self) {
        self.documents.write().clear();
        self.doc_freq.write().clear();
        *self.avg_doc_len.write() = 0.0;
    }

    /// Get the number of documents in the index
    pub fn len(&self) -> usize {
        self.documents.read().len()
    }

    /// Check if index is empty
    pub fn is_empty(&self) -> bool {
        self.documents.read().is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tokenize() {
        let tokens = BM25Index::tokenize("Hello, World! This is a test.");
        assert_eq!(tokens, vec!["hello", "world", "this", "is", "test"]);
    }

    #[test]
    fn test_add_and_search() {
        let index = BM25Index::new();
        index.add_document("1", "The quick brown fox jumps over the lazy dog");
        index.add_document("2", "A quick brown cat sleeps on the couch");
        index.add_document("3", "Python programming is fun and exciting");

        let results = index.search("quick brown", 10);
        assert_eq!(results.len(), 2);
        // Both docs 1 and 2 should match
        let ids: Vec<_> = results.iter().map(|(id, _)| id.as_str()).collect();
        assert!(ids.contains(&"1"));
        assert!(ids.contains(&"2"));
    }

    #[test]
    fn test_clear() {
        let index = BM25Index::new();
        index.add_document("1", "Test document");
        assert_eq!(index.len(), 1);

        index.clear();
        assert!(index.is_empty());
    }
}
