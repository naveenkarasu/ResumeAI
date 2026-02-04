package config

import (
	"os"
	"strconv"
	"time"

	"github.com/joho/godotenv"
	"gopkg.in/yaml.v3"
)

// Config holds all configuration for the application
type Config struct {
	Server    ServerConfig    `yaml:"server"`
	Database  DatabaseConfig  `yaml:"database"`
	MLService MLServiceConfig `yaml:"ml_service"`
	LLM       LLMConfig       `yaml:"llm"`
	Cache     CacheConfig     `yaml:"cache"`
	RateLimit RateLimitConfig `yaml:"rate_limit"`
	CORS      CORSConfig      `yaml:"cors"`
}

type ServerConfig struct {
	Host         string        `yaml:"host"`
	Port         int           `yaml:"port"`
	ReadTimeout  time.Duration `yaml:"read_timeout"`
	WriteTimeout time.Duration `yaml:"write_timeout"`
	Debug        bool          `yaml:"debug"`
}

type DatabaseConfig struct {
	Postgres PostgresConfig `yaml:"postgres"`
	Qdrant   QdrantConfig   `yaml:"qdrant"`
}

type PostgresConfig struct {
	Host     string `yaml:"host"`
	Port     int    `yaml:"port"`
	User     string `yaml:"user"`
	Password string `yaml:"password"`
	Database string `yaml:"database"`
	PoolSize int    `yaml:"pool_size"`
	SSLMode  string `yaml:"ssl_mode"`
}

func (p PostgresConfig) DSN() string {
	return "postgres://" + p.User + ":" + p.Password + "@" + p.Host + ":" +
		strconv.Itoa(p.Port) + "/" + p.Database + "?sslmode=" + p.SSLMode
}

type QdrantConfig struct {
	Host             string `yaml:"host"`
	Port             int    `yaml:"port"`
	CollectionPrefix string `yaml:"collection_prefix"`
}

type MLServiceConfig struct {
	Host    string        `yaml:"host"`
	Port    int           `yaml:"port"`
	Timeout time.Duration `yaml:"timeout"`
}

func (m MLServiceConfig) Address() string {
	return m.Host + ":" + strconv.Itoa(m.Port)
}

type LLMConfig struct {
	DefaultBackend string        `yaml:"default_backend"`
	Groq           GroqConfig    `yaml:"groq"`
	OpenAI         OpenAIConfig  `yaml:"openai"`
	Claude         ClaudeConfig  `yaml:"claude"`
	Timeout        time.Duration `yaml:"timeout"`
}

type GroqConfig struct {
	APIKey string `yaml:"api_key"`
	Model  string `yaml:"model"`
}

type OpenAIConfig struct {
	APIKey string `yaml:"api_key"`
	Model  string `yaml:"model"`
}

type ClaudeConfig struct {
	APIKey string `yaml:"api_key"`
	Model  string `yaml:"model"`
}

type CacheConfig struct {
	Enabled bool          `yaml:"enabled"`
	TTL     time.Duration `yaml:"ttl"`
	MaxSize int           `yaml:"max_size"`
}

type RateLimitConfig struct {
	Enabled           bool `yaml:"enabled"`
	RequestsPerMinute int  `yaml:"requests_per_minute"`
	Burst             int  `yaml:"burst"`
}

type CORSConfig struct {
	AllowedOrigins []string `yaml:"allowed_origins"`
	AllowedMethods []string `yaml:"allowed_methods"`
	AllowedHeaders []string `yaml:"allowed_headers"`
	MaxAge         int      `yaml:"max_age"`
}

// Load loads configuration from file and environment
func Load(configPath string) (*Config, error) {
	// Load .env file if it exists
	_ = godotenv.Load()

	cfg := defaultConfig()

	// Load from YAML file if provided
	if configPath != "" {
		data, err := os.ReadFile(configPath)
		if err == nil {
			if err := yaml.Unmarshal(data, cfg); err != nil {
				return nil, err
			}
		}
	}

	// Override with environment variables
	cfg.loadFromEnv()

	return cfg, nil
}

func defaultConfig() *Config {
	return &Config{
		Server: ServerConfig{
			Host:         "0.0.0.0",
			Port:         8080,
			ReadTimeout:  30 * time.Second,
			WriteTimeout: 30 * time.Second,
			Debug:        false,
		},
		Database: DatabaseConfig{
			Postgres: PostgresConfig{
				Host:     "localhost",
				Port:     5432,
				User:     "resume_rag",
				Password: "password",
				Database: "resume_rag",
				PoolSize: 25,
				SSLMode:  "disable",
			},
			Qdrant: QdrantConfig{
				Host:             "localhost",
				Port:             6333,
				CollectionPrefix: "resume_rag",
			},
		},
		MLService: MLServiceConfig{
			Host:    "localhost",
			Port:    50051,
			Timeout: 10 * time.Second,
		},
		LLM: LLMConfig{
			DefaultBackend: "groq",
			Groq: GroqConfig{
				Model: "llama-3.3-70b-versatile",
			},
			OpenAI: OpenAIConfig{
				Model: "gpt-4o-mini",
			},
			Claude: ClaudeConfig{
				Model: "claude-sonnet-4-20250514",
			},
			Timeout: 60 * time.Second,
		},
		Cache: CacheConfig{
			Enabled: true,
			TTL:     1 * time.Hour,
			MaxSize: 10000,
		},
		RateLimit: RateLimitConfig{
			Enabled:           true,
			RequestsPerMinute: 60,
			Burst:             10,
		},
		CORS: CORSConfig{
			AllowedOrigins: []string{"http://localhost:5173", "http://localhost:3000"},
			AllowedMethods: []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
			AllowedHeaders: []string{"*"},
			MaxAge:         600,
		},
	}
}

func (c *Config) loadFromEnv() {
	// Server
	if v := os.Getenv("SERVER_HOST"); v != "" {
		c.Server.Host = v
	}
	if v := os.Getenv("SERVER_PORT"); v != "" {
		if port, err := strconv.Atoi(v); err == nil {
			c.Server.Port = port
		}
	}
	if v := os.Getenv("DEBUG"); v == "true" {
		c.Server.Debug = true
	}

	// Database
	if v := os.Getenv("POSTGRES_HOST"); v != "" {
		c.Database.Postgres.Host = v
	}
	if v := os.Getenv("POSTGRES_PORT"); v != "" {
		if port, err := strconv.Atoi(v); err == nil {
			c.Database.Postgres.Port = port
		}
	}
	if v := os.Getenv("POSTGRES_USER"); v != "" {
		c.Database.Postgres.User = v
	}
	if v := os.Getenv("POSTGRES_PASSWORD"); v != "" {
		c.Database.Postgres.Password = v
	}
	if v := os.Getenv("POSTGRES_DB"); v != "" {
		c.Database.Postgres.Database = v
	}
	if v := os.Getenv("DATABASE_URL"); v != "" {
		// Parse DATABASE_URL if provided (for Docker/Heroku)
		// Format: postgres://user:password@host:port/database
		c.Database.Postgres.Host = v // Store raw URL, will parse in DSN()
	}

	// Qdrant
	if v := os.Getenv("QDRANT_HOST"); v != "" {
		c.Database.Qdrant.Host = v
	}
	if v := os.Getenv("QDRANT_PORT"); v != "" {
		if port, err := strconv.Atoi(v); err == nil {
			c.Database.Qdrant.Port = port
		}
	}

	// ML Service
	if v := os.Getenv("ML_SERVICE_HOST"); v != "" {
		c.MLService.Host = v
	}
	if v := os.Getenv("ML_SERVICE_PORT"); v != "" {
		if port, err := strconv.Atoi(v); err == nil {
			c.MLService.Port = port
		}
	}

	// LLM
	if v := os.Getenv("LLM_BACKEND"); v != "" {
		c.LLM.DefaultBackend = v
	}
	if v := os.Getenv("GROQ_API_KEY"); v != "" {
		c.LLM.Groq.APIKey = v
	}
	if v := os.Getenv("OPENAI_API_KEY"); v != "" {
		c.LLM.OpenAI.APIKey = v
	}
	if v := os.Getenv("ANTHROPIC_API_KEY"); v != "" {
		c.LLM.Claude.APIKey = v
	}
}
