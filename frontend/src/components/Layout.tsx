import { ReactNode } from 'react'
import { Link, useLocation, Outlet } from 'react-router-dom'
import { useState } from 'react'
import {
  LayoutDashboard,
  Newspaper,
  TrendingUp,
  BarChart3,
  Settings,
  Menu,
  X,
  Sun,
  Moon,
  Bell,
  Wifi,
  WifiOff
} from 'lucide-react'
import { useTheme } from '../hooks/useTheme'
import { useWebSocket } from '../hooks/useWebSocket'
import { useStore } from '../store'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'News', href: '/news', icon: Newspaper },
  { name: 'Predictions', href: '/predictions', icon: TrendingUp },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function Layout() {
  const location = useLocation()
  const { theme, toggleTheme } = useTheme()
  const { isConnected } = useWebSocket()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const notifications = useStore(state => state.notifications)

  return (
    <div className="min-h-screen bg-dark-50 dark:bg-dark-950">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-50 w-64 transform bg-white dark:bg-dark-900 border-r border-dark-200 dark:border-dark-700 transition-transform duration-300 lg:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex h-16 items-center justify-between px-4 border-b border-dark-200 dark:border-dark-700">
          <Link to="/" className="flex items-center gap-2 font-bold text-xl text-primary-600 dark:text-primary-400">
            <span className="text-2xl">📈</span>
            <span>ForexNews AI</span>
          </Link>
          <button
            className="lg:hidden p-2 rounded-lg hover:bg-dark-100 dark:hover:bg-dark-800"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="p-4 space-y-1">
          {navigation.map((item) => (
            <Link
              key={item.name}
              to={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                location.pathname === item.href
                  ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                  : 'text-dark-600 hover:bg-dark-100 dark:text-dark-400 dark:hover:bg-dark-800'
              }`}
            >
              <item.icon className="w-5 h-5" />
              {item.name}
            </Link>
          ))}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-dark-200 dark:border-dark-700">
          <div className="flex items-center gap-3 px-3 py-2 text-xs text-dark-500 dark:text-dark-400">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-bullish-500' : 'bg-bearish-500'}`} />
            <span>{isConnected ? 'Live' : 'Disconnected'}</span>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between px-4 border-b border-dark-200 dark:border-dark-700 bg-white/80 dark:bg-dark-900/80 backdrop-blur-sm">
          <button
            className="lg:hidden p-2 rounded-lg hover:bg-dark-100 dark:hover:bg-dark-800"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="w-6 h-6" />
          </button>

          <div className="flex-1 lg:flex-none" />

          <div className="flex items-center gap-4">
            {/* Notifications */}
            <button className="relative p-2 rounded-lg hover:bg-dark-100 dark:hover:bg-dark-800">
              <Bell className="w-5 h-5 text-dark-600 dark:text-dark-400" />
              {notifications.length > 0 && (
                <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-bearish-500 text-xs text-white">
                  {notifications.length > 9 ? '9+' : notifications.length}
                </span>
              )}
            </button>

            {/* Theme toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg hover:bg-dark-100 dark:hover:bg-dark-800"
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? (
                <Sun className="w-5 h-5 text-dark-600 dark:text-dark-400" />
              ) : (
                <Moon className="w-5 h-5 text-dark-600 dark:text-dark-400" />
              )}
            </button>

            {/* Connection status */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-dark-100 dark:bg-dark-800">
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-bullish-500' : 'bg-bearish-500'}`} />
              <span className="text-xs font-medium text-dark-600 dark:text-dark-400">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}