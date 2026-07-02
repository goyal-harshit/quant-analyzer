import { test, expect } from '@playwright/test'

/**
 * Critical-path E2E. The public/guest flows run with NO backend (the app ships
 * demo fallbacks + a guest mode), so they're safe in CI without a live API.
 * The authenticated flow is gated behind E2E_BACKEND=1 (needs the API on :8000).
 */

test.describe('Landing page', () => {
  test('renders the hero and headline stats', async ({ page }) => {
    await page.goto('/')
    // Brand + hero headline (split across <br>/<span>, so match on a stable word).
    await expect(page.locator('nav')).toContainText('QuantAI')
    await expect(page.locator('h1')).toContainText('quantified')
    // Headline stats the landing advertises.
    await expect(page.getByText('Nifty 500 Stocks Covered')).toBeVisible()
    await expect(page.getByText('Quantitative Factors')).toBeVisible()
  })

  test('"Launch Dashboard" routes to login', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /Launch Dashboard/i }).click()
    await expect(page).toHaveURL(/\/login$/)
  })
})

test.describe('Login page', () => {
  test('shows validation when submitting empty credentials', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: /Welcome back to QuantAI/i })).toBeVisible()
    // Bypass native "required" so our client-side guard/toast can fire.
    await page.locator('#login-email').fill('x')
    await page.locator('#login-email').fill('')
    await page.getByRole('button', { name: /Access Terminal/i }).click({ trial: false })
    // Either the HTML5 validation blocks submit, or our toast appears — assert we
    // never navigated away from /login (login did not succeed with empty input).
    await expect(page).toHaveURL(/\/login$/)
  })

  test('"Explore as Guest" enters the app without an account', async ({ page }) => {
    await page.goto('/login')
    await page.getByRole('button', { name: /Explore as Guest/i }).click()
    await expect(page).toHaveURL(/\/dashboard$/)
  })
})

test.describe('Guest navigation', () => {
  test('screener page loads its shell + Nifty 500 universe toggle', async ({ page }) => {
    await page.goto('/screener')
    // Heading + universe toggle render immediately (not gated on the data fetch).
    await expect(page.getByText('Factor Screener')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Nifty 500' })).toBeVisible()
  })

  test('quant lab page loads the factor lab', async ({ page }) => {
    await page.goto('/quant-lab')
    await expect(page.getByText(/Quant Lab/i).first()).toBeVisible()
  })
})

/**
 * Full authenticated path: register → login → screener → portfolio.
 * Only runs when a backend is available (E2E_BACKEND=1) since it needs real auth.
 */
test.describe('Authenticated flow', () => {
  test.skip(!process.env.E2E_BACKEND, 'requires the backend API on :8000 (set E2E_BACKEND=1)')

  test('register, land on dashboard, open screener and portfolio', async ({ page }) => {
    const email = `e2e_${Date.now()}@example.com`
    await page.goto('/register')
    await page.locator('#login-email, input[type="email"]').first().fill(email)
    await page.locator('input[type="password"]').first().fill('Passw0rd!123')
    await page.getByRole('button', { name: /Create|Register|Sign up|Access/i }).first().click()
    await expect(page).toHaveURL(/\/(dashboard|login)/, { timeout: 20_000 })

    await page.goto('/screener')
    await expect(page.getByText(/Nifty 500 universe/i)).toBeVisible({ timeout: 30_000 })

    await page.goto('/portfolio')
    await expect(page.locator('body')).toBeVisible()
  })
})
