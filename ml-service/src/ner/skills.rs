use anyhow::Result;
use once_cell::sync::Lazy;
use regex::Regex;
use std::collections::HashSet;
use tracing::debug;

/// Extracted skills categorized by type
#[derive(Debug, Clone, Default)]
pub struct ExtractedSkills {
    pub technical_skills: Vec<String>,
    pub soft_skills: Vec<String>,
    pub tools: Vec<String>,
    pub frameworks: Vec<String>,
    pub languages: Vec<String>,
}

/// Skill extractor using pattern matching and keyword lists
/// In production, this could be replaced with a proper NER model
pub struct SkillExtractor {
    programming_languages: HashSet<String>,
    frameworks: HashSet<String>,
    tools: HashSet<String>,
    soft_skills: HashSet<String>,
    technical_skills: HashSet<String>,
}

// Common programming languages
static PROGRAMMING_LANGUAGES: Lazy<HashSet<String>> = Lazy::new(|| {
    [
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "golang",
        "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl",
        "haskell", "erlang", "elixir", "clojure", "f#", "dart", "lua", "groovy",
        "objective-c", "assembly", "cobol", "fortran", "lisp", "prolog", "sql",
        "bash", "powershell", "shell", "html", "css", "sass", "less", "graphql",
    ]
    .iter()
    .map(|s| s.to_string())
    .collect()
});

// Common frameworks
static FRAMEWORKS: Lazy<HashSet<String>> = Lazy::new(|| {
    [
        "react", "reactjs", "react.js", "angular", "angularjs", "vue", "vuejs",
        "vue.js", "svelte", "nextjs", "next.js", "nuxt", "nuxtjs", "gatsby",
        "django", "flask", "fastapi", "express", "expressjs", "nestjs", "nest.js",
        "spring", "spring boot", "springboot", "rails", "ruby on rails", "laravel",
        "symfony", "asp.net", "dotnet", ".net", ".net core", "blazor", "gin",
        "echo", "fiber", "actix", "axum", "rocket", "tokio", "tensorflow",
        "pytorch", "keras", "scikit-learn", "sklearn", "pandas", "numpy",
        "spark", "hadoop", "flink", "kafka", "rabbitmq", "celery", "airflow",
        "bootstrap", "tailwind", "tailwindcss", "material-ui", "mui", "chakra",
        "ant design", "styled-components", "emotion", "redux", "mobx", "zustand",
        "rxjs", "jquery", "backbone", "ember", "meteor", "phoenix", "ktor",
    ]
    .iter()
    .map(|s| s.to_string())
    .collect()
});

// Common tools
static TOOLS: Lazy<HashSet<String>> = Lazy::new(|| {
    [
        "git", "github", "gitlab", "bitbucket", "svn", "mercurial", "docker",
        "kubernetes", "k8s", "helm", "terraform", "ansible", "puppet", "chef",
        "jenkins", "circleci", "travisci", "github actions", "gitlab ci",
        "azure devops", "aws", "azure", "gcp", "google cloud", "heroku",
        "vercel", "netlify", "digitalocean", "linode", "cloudflare", "nginx",
        "apache", "tomcat", "iis", "redis", "memcached", "elasticsearch",
        "kibana", "logstash", "grafana", "prometheus", "datadog", "splunk",
        "new relic", "sentry", "jira", "confluence", "trello", "asana",
        "slack", "teams", "zoom", "figma", "sketch", "adobe xd", "photoshop",
        "illustrator", "vs code", "vscode", "visual studio", "intellij",
        "pycharm", "webstorm", "eclipse", "vim", "emacs", "sublime", "atom",
        "postman", "insomnia", "swagger", "openapi", "graphql playground",
        "mysql", "postgresql", "postgres", "mongodb", "cassandra", "dynamodb",
        "firebase", "supabase", "sqlite", "oracle", "sql server", "mariadb",
        "neo4j", "couchdb", "influxdb", "timescaledb", "cockroachdb",
        "webpack", "vite", "rollup", "parcel", "esbuild", "babel", "eslint",
        "prettier", "jest", "mocha", "cypress", "playwright", "selenium",
        "pytest", "unittest", "junit", "testng", "rspec", "phpunit",
        "linux", "ubuntu", "centos", "debian", "macos", "windows server",
    ]
    .iter()
    .map(|s| s.to_string())
    .collect()
});

// Soft skills
static SOFT_SKILLS: Lazy<HashSet<String>> = Lazy::new(|| {
    [
        "leadership", "communication", "teamwork", "collaboration", "problem-solving",
        "problem solving", "critical thinking", "creativity", "adaptability",
        "time management", "organization", "attention to detail", "multitasking",
        "decision making", "decision-making", "conflict resolution", "negotiation",
        "presentation", "public speaking", "written communication", "interpersonal",
        "emotional intelligence", "empathy", "mentoring", "coaching", "training",
        "project management", "agile", "scrum", "kanban", "waterfall", "lean",
        "stakeholder management", "client relations", "customer service",
        "cross-functional", "remote work", "self-motivated", "initiative",
        "analytical", "strategic thinking", "innovation", "continuous learning",
    ]
    .iter()
    .map(|s| s.to_string())
    .collect()
});

// Technical skills (beyond languages/frameworks/tools)
static TECHNICAL_SKILLS: Lazy<HashSet<String>> = Lazy::new(|| {
    [
        "machine learning", "ml", "deep learning", "neural networks", "nlp",
        "natural language processing", "computer vision", "cv", "data science",
        "data analysis", "data engineering", "etl", "data visualization",
        "statistics", "a/b testing", "ab testing", "experimentation",
        "api design", "rest", "restful", "microservices", "monolith",
        "distributed systems", "cloud computing", "serverless", "saas", "paas",
        "devops", "devsecops", "sre", "site reliability", "ci/cd", "cicd",
        "infrastructure as code", "iac", "automation", "scripting",
        "security", "cybersecurity", "penetration testing", "encryption",
        "authentication", "authorization", "oauth", "jwt", "sso", "saml",
        "database design", "data modeling", "orm", "query optimization",
        "caching", "cdn", "load balancing", "high availability", "scalability",
        "performance optimization", "profiling", "debugging", "monitoring",
        "logging", "observability", "tracing", "incident response",
        "code review", "pair programming", "tdd", "bdd", "ddd", "solid",
        "design patterns", "clean code", "refactoring", "technical debt",
        "system design", "architecture", "frontend", "backend", "full stack",
        "fullstack", "mobile development", "ios", "android", "react native",
        "flutter", "cross-platform", "responsive design", "accessibility",
        "seo", "web performance", "pwa", "progressive web apps",
        "version control", "branching strategies", "gitflow", "trunk-based",
        "documentation", "technical writing", "api documentation",
        "blockchain", "smart contracts", "web3", "cryptocurrency",
        "iot", "embedded systems", "firmware", "hardware", "fpga",
        "game development", "graphics programming", "opengl", "vulkan",
        "ar", "vr", "augmented reality", "virtual reality", "3d modeling",
    ]
    .iter()
    .map(|s| s.to_string())
    .collect()
});

impl Default for SkillExtractor {
    fn default() -> Self {
        Self::new()
    }
}

impl SkillExtractor {
    pub fn new() -> Self {
        Self {
            programming_languages: PROGRAMMING_LANGUAGES.clone(),
            frameworks: FRAMEWORKS.clone(),
            tools: TOOLS.clone(),
            soft_skills: SOFT_SKILLS.clone(),
            technical_skills: TECHNICAL_SKILLS.clone(),
        }
    }

    /// Extract skills from text
    pub fn extract(&self, text: &str, include_soft_skills: bool) -> ExtractedSkills {
        debug!("Extracting skills from text ({} chars)", text.len());

        let text_lower = text.to_lowercase();
        let words = self.tokenize(&text_lower);

        let mut result = ExtractedSkills::default();

        // Extract programming languages
        result.languages = self.extract_matches(&words, &text_lower, &self.programming_languages);

        // Extract frameworks
        result.frameworks = self.extract_matches(&words, &text_lower, &self.frameworks);

        // Extract tools
        result.tools = self.extract_matches(&words, &text_lower, &self.tools);

        // Extract technical skills
        result.technical_skills = self.extract_matches(&words, &text_lower, &self.technical_skills);

        // Extract soft skills if requested
        if include_soft_skills {
            result.soft_skills = self.extract_matches(&words, &text_lower, &self.soft_skills);
        }

        debug!(
            "Extracted {} languages, {} frameworks, {} tools, {} technical, {} soft skills",
            result.languages.len(),
            result.frameworks.len(),
            result.tools.len(),
            result.technical_skills.len(),
            result.soft_skills.len()
        );

        result
    }

    /// Tokenize text into words
    fn tokenize(&self, text: &str) -> Vec<String> {
        static WORD_RE: Lazy<Regex> = Lazy::new(|| Regex::new(r"[a-z0-9#+.-]+").unwrap());

        WORD_RE
            .find_iter(text)
            .map(|m| m.as_str().to_string())
            .collect()
    }

    /// Extract matches for multi-word and single-word skills
    fn extract_matches(
        &self,
        words: &[String],
        text: &str,
        skill_set: &HashSet<String>,
    ) -> Vec<String> {
        let mut found = HashSet::new();

        // Check for multi-word skills in the full text
        for skill in skill_set {
            if skill.contains(' ') || skill.contains('-') || skill.contains('.') {
                if text.contains(skill) {
                    found.insert(skill.clone());
                }
            }
        }

        // Check single words
        for word in words {
            if skill_set.contains(word) {
                found.insert(word.clone());
            }
        }

        let mut result: Vec<String> = found.into_iter().collect();
        result.sort();
        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_programming_languages() {
        let extractor = SkillExtractor::new();
        let text = "I am proficient in Python, JavaScript, and Rust. I also know some Go.";
        let skills = extractor.extract(text, false);

        assert!(skills.languages.contains(&"python".to_string()));
        assert!(skills.languages.contains(&"javascript".to_string()));
        assert!(skills.languages.contains(&"rust".to_string()));
        assert!(skills.languages.contains(&"go".to_string()));
    }

    #[test]
    fn test_extract_frameworks() {
        let extractor = SkillExtractor::new();
        let text = "Experience with React, Django, and FastAPI. Built apps using Next.js";
        let skills = extractor.extract(text, false);

        assert!(skills.frameworks.contains(&"react".to_string()));
        assert!(skills.frameworks.contains(&"django".to_string()));
        assert!(skills.frameworks.contains(&"fastapi".to_string()));
    }

    #[test]
    fn test_extract_tools() {
        let extractor = SkillExtractor::new();
        let text = "Used Docker and Kubernetes for deployment. AWS and PostgreSQL for infrastructure.";
        let skills = extractor.extract(text, false);

        assert!(skills.tools.contains(&"docker".to_string()));
        assert!(skills.tools.contains(&"kubernetes".to_string()));
        assert!(skills.tools.contains(&"aws".to_string()));
        assert!(skills.tools.contains(&"postgresql".to_string()));
    }

    #[test]
    fn test_extract_soft_skills() {
        let extractor = SkillExtractor::new();
        let text = "Strong leadership and communication skills. Experience with agile methodologies.";
        let skills = extractor.extract(text, true);

        assert!(skills.soft_skills.contains(&"leadership".to_string()));
        assert!(skills.soft_skills.contains(&"communication".to_string()));
        assert!(skills.soft_skills.contains(&"agile".to_string()));
    }

    #[test]
    fn test_no_soft_skills_when_disabled() {
        let extractor = SkillExtractor::new();
        let text = "Strong leadership and communication skills.";
        let skills = extractor.extract(text, false);

        assert!(skills.soft_skills.is_empty());
    }
}
