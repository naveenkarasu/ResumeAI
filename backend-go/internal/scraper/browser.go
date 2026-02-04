package scraper

import (
	"context"
	"fmt"
	"time"

	"github.com/chromedp/cdproto/cdp"
	"github.com/chromedp/cdproto/dom"
	"github.com/chromedp/chromedp"
	"go.uber.org/zap"
)

// BrowserPool manages a pool of browser contexts
type BrowserPool struct {
	allocCtx context.Context
	cancel   context.CancelFunc
	logger   *zap.Logger
	opts     []chromedp.ExecAllocatorOption
}

// BrowserConfig configures browser behavior
type BrowserConfig struct {
	Headless        bool
	Timeout         time.Duration
	UserAgent       string
	ProxyURL        string
	DisableImages   bool
	DisableJS       bool
	WindowWidth     int
	WindowHeight    int
}

// DefaultBrowserConfig returns sensible defaults
func DefaultBrowserConfig() *BrowserConfig {
	return &BrowserConfig{
		Headless:      true,
		Timeout:       30 * time.Second,
		UserAgent:     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
		DisableImages: true,
		DisableJS:     false,
		WindowWidth:   1920,
		WindowHeight:  1080,
	}
}

// NewBrowserPool creates a new browser pool
func NewBrowserPool(logger *zap.Logger, config *BrowserConfig) (*BrowserPool, error) {
	if config == nil {
		config = DefaultBrowserConfig()
	}

	opts := []chromedp.ExecAllocatorOption{
		chromedp.NoFirstRun,
		chromedp.NoDefaultBrowserCheck,
		chromedp.DisableGPU,
		chromedp.NoSandbox,
		chromedp.Headless,
		chromedp.UserAgent(config.UserAgent),
		chromedp.WindowSize(config.WindowWidth, config.WindowHeight),
	}

	if config.ProxyURL != "" {
		opts = append(opts, chromedp.ProxyServer(config.ProxyURL))
	}

	if config.DisableImages {
		opts = append(opts, chromedp.Flag("blink-settings", "imagesEnabled=false"))
	}

	allocCtx, cancel := chromedp.NewExecAllocator(context.Background(), opts...)

	return &BrowserPool{
		allocCtx: allocCtx,
		cancel:   cancel,
		logger:   logger,
		opts:     opts,
	}, nil
}

// Close shuts down the browser pool
func (p *BrowserPool) Close() {
	p.cancel()
}

// NewContext creates a new browser context from the pool
func (p *BrowserPool) NewContext(timeout time.Duration) (context.Context, context.CancelFunc) {
	ctx, cancel := chromedp.NewContext(p.allocCtx)
	if timeout > 0 {
		ctx, cancel = context.WithTimeout(ctx, timeout)
	}
	return ctx, cancel
}

// FetchPage fetches a page and returns its HTML content
func (p *BrowserPool) FetchPage(ctx context.Context, url string, waitSelector string) (string, error) {
	p.logger.Debug("Fetching page", zap.String("url", url))

	var html string

	actions := []chromedp.Action{
		chromedp.Navigate(url),
	}

	// Wait for selector if provided
	if waitSelector != "" {
		actions = append(actions, chromedp.WaitVisible(waitSelector, chromedp.ByQuery))
	} else {
		actions = append(actions, chromedp.WaitReady("body", chromedp.ByQuery))
	}

	// Get HTML
	actions = append(actions, chromedp.ActionFunc(func(ctx context.Context) error {
		node, err := dom.GetDocument().Do(ctx)
		if err != nil {
			return err
		}
		html, err = dom.GetOuterHTML().WithNodeID(node.NodeID).Do(ctx)
		return err
	}))

	if err := chromedp.Run(ctx, actions...); err != nil {
		return "", fmt.Errorf("failed to fetch page: %w", err)
	}

	p.logger.Debug("Page fetched", zap.String("url", url), zap.Int("length", len(html)))
	return html, nil
}

// ClickAndWait clicks an element and waits for page load
func (p *BrowserPool) ClickAndWait(ctx context.Context, selector string, waitSelector string) error {
	actions := []chromedp.Action{
		chromedp.Click(selector, chromedp.ByQuery),
	}

	if waitSelector != "" {
		actions = append(actions, chromedp.WaitVisible(waitSelector, chromedp.ByQuery))
	} else {
		actions = append(actions, chromedp.Sleep(1*time.Second))
	}

	return chromedp.Run(ctx, actions...)
}

// ScrollToBottom scrolls the page to load lazy content
func (p *BrowserPool) ScrollToBottom(ctx context.Context, maxScrolls int, delay time.Duration) error {
	for i := 0; i < maxScrolls; i++ {
		if err := chromedp.Run(ctx,
			chromedp.Evaluate(`window.scrollTo(0, document.body.scrollHeight)`, nil),
			chromedp.Sleep(delay),
		); err != nil {
			return err
		}
	}
	return nil
}

// FillForm fills a form field
func (p *BrowserPool) FillForm(ctx context.Context, selector, value string) error {
	return chromedp.Run(ctx,
		chromedp.WaitVisible(selector, chromedp.ByQuery),
		chromedp.Clear(selector, chromedp.ByQuery),
		chromedp.SendKeys(selector, value, chromedp.ByQuery),
	)
}

// GetText extracts text content from an element
func (p *BrowserPool) GetText(ctx context.Context, selector string) (string, error) {
	var text string
	if err := chromedp.Run(ctx,
		chromedp.Text(selector, &text, chromedp.ByQuery),
	); err != nil {
		return "", err
	}
	return text, nil
}

// GetAttribute extracts an attribute from an element
func (p *BrowserPool) GetAttribute(ctx context.Context, selector, attr string) (string, error) {
	var value string
	if err := chromedp.Run(ctx,
		chromedp.AttributeValue(selector, attr, &value, nil, chromedp.ByQuery),
	); err != nil {
		return "", err
	}
	return value, nil
}

// GetElements returns all elements matching a selector
func (p *BrowserPool) GetElements(ctx context.Context, selector string) ([]string, error) {
	var nodes []*cdp.Node
	if err := chromedp.Run(ctx,
		chromedp.Nodes(selector, &nodes, chromedp.ByQueryAll),
	); err != nil {
		return nil, err
	}

	var results []string
	for _, node := range nodes {
		var html string
		if err := chromedp.Run(ctx,
			chromedp.OuterHTML(node.FullXPath(), &html),
		); err == nil {
			results = append(results, html)
		}
	}
	return results, nil
}

// WaitForElement waits for an element to appear
func (p *BrowserPool) WaitForElement(ctx context.Context, selector string, timeout time.Duration) error {
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	return chromedp.Run(ctx,
		chromedp.WaitVisible(selector, chromedp.ByQuery),
	)
}

// Screenshot takes a screenshot of the current page (useful for debugging)
func (p *BrowserPool) Screenshot(ctx context.Context) ([]byte, error) {
	var buf []byte
	if err := chromedp.Run(ctx,
		chromedp.CaptureScreenshot(&buf),
	); err != nil {
		return nil, err
	}
	return buf, nil
}
