const KEY = 'niar-theme'

export type Theme = 'light' | 'dark'

export function getTheme(): Theme {
  return (localStorage.getItem(KEY) as Theme) || 'light'
}

export function applyTheme(theme: Theme): void {
  const html = document.documentElement
  if (theme === 'dark') {
    html.classList.add('dark')
  } else {
    html.classList.remove('dark')
  }
}

export function setTheme(theme: Theme): void {
  localStorage.setItem(KEY, theme)
  applyTheme(theme)
}

export function applySavedTheme(): void {
  applyTheme(getTheme())
}

