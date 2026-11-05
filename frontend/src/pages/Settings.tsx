import { useState } from 'react'
import {
  User,
  Bell,
  Shield,
  Palette,
  Database,
  Terminal,
  Save,
  Loader2,
  Key,
  Globe,
  Moon,
  Sun,
  Monitor,
  HardDrive,
  Wifi,
  WifiOff
} from 'lucide-react'
import { useTheme } from '../hooks/useTheme'
import { useWebSocket } from '../hooks/useWebSocket'
import { useStore } from '../store'

export function Settings() {
  const { theme, toggleTheme } = useTheme()
  const { isConnected } = useWebSocket()
  const clearStore = useStore(state => {
    state.prices = {}
    state.predictions = []
    state.news = []
    state.sentiments = {}
    state.notifications = []
  })
  const [saving, setSaving] = useState(false)
  const [settings, setSettings] = useState({
    // General
    autoRefresh: true,
    refreshInterval: 30,
    compactMode: false,
    showTooltips: true,

    // Notifications
    notifyPredictions: true,
    notifyNews: true,
    notifyResolved: true,
    notifyErrors: true,
    soundEnabled: false,

    // Display
    chartType: 'line',
    showVolume: false,
    showIndicators: true,
    priceDecimals: 5,
    timezone: 'UTC',

    // Data
    defaultPairs: ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD'],
    maxNewsItems: 100,
    maxPredictions: 50,
    cacheTimeout: 300,

    // API
    apiUrl: 'http://localhost:8000/api/v1',
    wsUrl: 'ws://localhost:8000',
    apiKey: '',

    // Advanced
    debugMode: false,
    logLevel: 'info',
    enableWebGL: true,
  })

  const handleChange = (key: string, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    setSaving(true)
    // Save to localStorage
    localStorage.setItem('forexnews-settings', JSON.stringify(settings))
    // In a real app, this would call an API
    await new Promise(resolve => setTimeout(resolve, 500))
    setSaving(false)
  }

  const handleClearData = () => {
    if (confirm('This will clear all cached data. Are you sure?')) {
      clearStore()
      localStorage.removeItem('forexnews-store')
    }
  }

  const handleResetSettings = () => {
    if (confirm('Reset all settings to defaults?')) {
      localStorage.removeItem('forexnews-settings')
      window.location.reload()
    }
  }

  const tabs = [
    { id: 'general', label: 'General', icon: Monitor },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'display', label: 'Display', icon: Palette },
    { id: 'data', label: 'Data', icon: Database },
    { id: 'api', label: 'API', icon: Terminal },
    { id: 'advanced', label: 'Advanced', icon: Shield },
  ]

  const [activeTab, setActiveTab] = useState('general')

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-dark-900 dark:text-dark-100">Settings</h1>
          <p className="text-dark-500 dark:text-dark-400">Configure your ForexNews AI experience</p>
        </div>
        <button onClick={handleSave} disabled={saving} className="btn-primary">
          <Save className="w-4 h-4 mr-2" />
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-dark-100 dark:bg-dark-800 rounded-lg p-1 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors whitespace-nowrap ${
              activeTab === tab.id
                ? 'bg-white dark:bg-dark-900 shadow-sm text-dark-900 dark:text-dark-100'
                : 'text-dark-600 dark:text-dark-400 hover:text-dark-900 dark:hover:text-dark-100'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="card">
        {activeTab === 'general' && (
          <SettingsSection title="General Settings">
            <SettingRow>
              <SettingLabel
                title="Auto Refresh"
                description="Automatically refresh data at regular intervals"
              />
              <Toggle
                checked={settings.autoRefresh}
                onChange={(e) => handleChange('autoRefresh', e.target.checked)}
              />
            </SettingRow>

            <SettingRow>
              <SettingLabel
                title="Refresh Interval (seconds)"
                description="How often to fetch new data"
              />
              <input
                type="number"
                value={settings.refreshInterval}
                onChange={(e) => handleChange('refreshInterval', parseInt(e.target.value))}
                min={5}
                max={300}
                className="input w-24"
                disabled={!settings.autoRefresh}
              />
            </SettingRow>

            <SettingRow>
              <SettingLabel
                title="Compact Mode"
                description="Reduce spacing for more data density"
              />
              <Toggle
                checked={settings.compactMode}
                onChange={(e) => handleChange('compactMode', e.target.checked)}
              />
            </SettingRow>

            <SettingRow>
              <SettingLabel
                title="Show Tooltips"
                description="Display helpful tooltips on hover"
              />
              <Toggle
                checked={settings.showTooltips}
                onChange={(e) => handleChange('showTooltips', e.target.checked)}
              />
            </SettingRow>

            <SettingRow>
              <SettingLabel
                title="Theme"
                description="Choose your preferred color theme"
              />
              <div className="flex items-center gap-4">
                <label className={`flex items-center gap-2 cursor-pointer ${theme === 'light' ? 'text-primary-600' : 'text-dark-500'}`}>
                  <input
                    type="radio"
                    name="theme"
                    value="light"
                    checked={theme === 'light'}
                    onChange={() => toggleTheme()}
                    className="sr-only"
                  />
                  <span className="flex items-center gap-2 px-3 py-2 rounded-lg border border-dark-200 dark:border-dark-700 bg-white dark:bg-dark-900">
                    <Sun className="w-4 h-4" />
                    Light
                  </span>
                </label>
                <label className={`flex items-center gap-2 cursor-pointer ${theme === 'dark' ? 'text-primary-600' : 'text-dark-500'}`}>
                  <input
                    type="radio"
                    name="theme"
                    value="dark"
                    checked={theme === 'dark'}
                    onChange={() => toggleTheme()}
                    className="sr-only"
                  />
                  <span className="flex items-center gap-2 px-3 py-2 rounded-lg border border-dark-200 dark:border-dark-700 bg-white dark:bg-dark-900">
                    <Moon className="w-4 h-4" />
                    Dark
                  </span>
                </label>
                <label className={`flex items-center gap-2 cursor-pointer ${theme === 'system' ? 'text-primary-600' : 'text-dark-500'}`}>
                  <input
                    type="radio"
                    name="theme"
                    value="system"
                    checked={theme === 'system'}
                    onChange={() => {}}
                    className="sr-only"
                  />
                  <span className="flex items-center gap-2 px-3 py-2 rounded-lg border border-dark-200 dark:border-dark-700 bg-white dark:bg-dark-900">
                    <Monitor className="w-4 h-4" />
                    System
                  </span>
                </label>
              </div>
            </SettingRow>

            <SettingRow>
              <SettingLabel
                title="Timezone"
                description="Timezone for displaying timestamps"
              />
              <select
                value={settings.timezone}
                onChange={(e) => handleChange('timezone', e.target.value)}
                className="input w-48"
              >
                <option value="UTC">UTC</option>
                <option value="America/New_York">Eastern Time (ET)</option>
                <option value="America/Chicago">Central Time (CT)</option>
                <option value="America/Denver">Mountain Time (MT)</option>
                <option value="America/Los_Angeles">Pacific Time (PT)</option>
                <option value="Europe/London">London (GMT/BST)</option>
                <option value="Europe/Paris">Paris (CET/CEST)</option>
                <option value="Asia/Tokyo">Tokyo (JST)</option>
                <option value="Asia/Singapore">Singapore (SGT)</option>
                <option value="Australia/Sydney">Sydney (AEST/AEDT)</option>
              </select>
            </SettingRow>
          </SettingsSection>
        )}

        {activeTab === 'notifications' && (
          <SettingsSection title="Notification Settings">
            <SettingRow>
              <SettingLabel
                title="New Predictions"
                description="Notify when new predictions are generated"
              />
              <Toggle
                checked={settings.notifyPredictions}
                onChange={(e) => handleChange('notifyPredictions', e.target.checked)}
              />
            </SettingRow>

            <SettingRow>
              <SettingLabel
                title="Breaking News"
                description="Notify on high-impact news releases"
              />
              <Toggle
                checked={settings.notifyNews}
                onChange={(e) => handleChange('notifyNews', e.target.checked)}
              />
            </SettingRow>

            <SettingRow>
              <SettingLabel
                title="Prediction Resolved"
                description="Notify when predictions expire and are resolved"
              />
              <Toggle
                checked={settings.notifyResolved}
                onChange={(e) => handleChange('notifyResolved', e.target.checked)}
              />
            </SettingRow>

            <SettingRow>
              <SettingLabel
                title="Errors"
                description="Notify on connection errors or API failures"
              />
              <Toggle
                checked={settings.notifyErrors}
                onChange={(e) => handleChange('notifyErrors', e.target.checked)}
              />
            </SettingRow>

            <SettingRow>
              <SettingLabel
                title="Sound Effects"
                description="Play sounds for notifications"
              />
              <Toggle
                checked={settings.soundEnabled}
                onChange={(e) => handleChange('soundEnabled', e.target.checked)}
              />
            </SettingRow>
          </SettingsSection>
        )}

        {activeTab === 'display' && (
          <SettingsSection title="Display Settings">
            <SettingRow>
              <SettingLabel
                title="Chart Type"
                description="Default chart visualization style"
              />
              <select
                value={settings.chartType}
                onChange={(e) => handleChange('chartType', e.target.value)}
                className="input w-48"
              >
                <option value="line">Line Chart</option>
                <option value="area">Area Chart</option>
                <option value="candlestick">Candlestick</option>
                <option value="heikin-ashi">Heikin Ashi</option>
              </select>
            </SettingRow>

            <SettingRow>
              <SettingLabel
                title="Show Volume"
                description="Display volume bars on charts"
              />
              <Toggle
                checked={settings.showVolume}
                onChange={(e) => handleChange('showVolume', e.target.checked)}
              />
            </SettingRow>

            <SettingRow>
              <SettingLabel
                title="Show Indicators"
                description="Display technical indicators by default"
              />
              <Toggle
                checked={settings.showIndicators}
                onChange={(e) => handleChange('showIndicators', e.target.checked)}
              />
            </SettingRow>

            <SettingRow>
              <SettingLabel
                title="Price Decimals"
                description="Number of decimal places for price display"
              />
              <select
                value={settings.priceDecimals}
                onChange={(e) => handleChange('priceDecimals', parseInt(e.target.value))}
                className="input w-24"
              >
                <option value={3}>3</option>
                <option value={4}>4</option>
                <option value={5}>5</option>
                <option value={6}>6</option>
              </select>
            </SettingRow>
          </SettingsSection>
        )}

        {activeTab === 'data' && (
          <SettingsSection title="Data Settings">
            <SettingRow>
              <SettingLabel
                title="Default Pairs"
                description="Pairs to show by default on dashboard"
              />
              <div className="flex flex-wrap gap-2">
                {['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD', 'EURGBP', 'EURJPY', 'GBPJPY'].map(pair => (
                  <label key={pair} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.defaultPairs.includes(pair)}
                      onChange={(e) => handleChange('defaultPairs',
                        e.target.checked
                          ? [...settings.defaultPairs, pair]
                          : settings.defaultPairs.filter(p => p !== pair)
                      )}
                      className="rounded border-dark-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span className="text-sm font-mono">{pair}</span>
                  </label>
                ))}
              </div>
            </SettingRow>

            <SettingRow>
              <SettingLabel
                title="Max News Items"
                description="Maximum news articles to keep in memory"
              />
              <input
                type="number"
                value={settings.maxNewsItems}
                onChange={(e) => handleChange('maxNewsItems', parseInt(e.target.value))}
                min={10}
                max={1000}
                className="input w-24"
              />
            </SettingRow>

            <SettingRow>
              <SettingLabel
                title="Max Predictions"
                description="Maximum predictions to keep in memory"
              />
              <input
                type="number"
                value={settings.maxPredictions}
                onChange={(e) => handleChange('maxPredictions', parseInt(e.target.value))}
                min={10}
                max={500}
                className="input w-24"
              />
            </SettingRow>

            <SettingRow>
              <SettingLabel
                title="Cache Timeout (seconds)"
                description="How long to cache API responses"
              />
              <input
                type="number"
                value={settings.cacheTimeout}
                onChange={(e) => handleChange('cacheTimeout', parseInt(e.target.value))}
                min={30}
                max={3600}
                className="input w-24"
              />
            </SettingRow>

            <div className="pt-4 border-t border-dark-200 dark:border-dark-700">
              <button onClick={handleClearData} className="btn-danger">
                <HardDrive className="w-4 h-4 mr-2" />
                Clear All Cached Data
              </button>
            </div>
          </SettingsSection>
        )}

        {activeTab === 'api' && (
          <SettingsSection title="API Configuration">
            <div className="mb-6 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
              <p className="text-sm text-amber-800 dark:text-amber-200">
                <strong>Note:</strong> These settings require a backend restart to take effect.
                For production, configure these via environment variables on the server.
              </p>
            </div>

            <SettingRow>
              <SettingLabel
                title="API Base URL"
                description="Backend API endpoint"
              />
              <input
                type="url"
                value={settings.apiUrl}
                onChange={(e) => handleChange('apiUrl', e.target.value)}
                className="input w-full max-w-md"
              />
            </SettingRow>

            <SettingRow>
              <SettingLabel
                title="WebSocket URL"
                description="WebSocket endpoint for real-time updates"
              />
              <input
                type="url"
                value={settings.wsUrl}
                onChange={(e) => handleChange('wsUrl', e.target.value)}
                className="input w-full max-w-md"
              />
            </SettingRow>

            <SettingRow>
              <SettingLabel
                title="API Key"
                description="Authentication key for API access (if required)"
              />
              <div className="relative">
                <input
                  type="password"
                  value={settings.apiKey}
                  onChange={(e) => handleChange('apiKey', e.target.value)}
                  className="input w-full max-w-md pr-10"
                  placeholder="Enter API key..."
                />
                <Key className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-400" />
              </div>
            </SettingRow>

            <div className="pt-4">
              <h4 className="font-medium text-dark-900 dark:text-dark-100 mb-2">Connection Status</h4>
              <div className="flex items-center gap-4 p-4 rounded-lg bg-dark-50 dark:bg-dark-800/50">
                <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-bullish-500' : 'bg-bearish-500'}`} />
                <span className="text-dark-600 dark:text-dark-400">
                  {isConnected ? 'Connected to WebSocket' : 'Disconnected'}
                </span>
                <span className="text-sm text-dark-400 ml-auto">
                  {isConnected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
                </span>
              </div>
            </div>
          </SettingsSection>
        )}

        {activeTab === 'advanced' && (
          <SettingsSection title="Advanced Settings">
            <SettingRow>
              <SettingLabel
                title="Debug Mode"
                description="Enable debug logging and development tools"
              />
              <Toggle
                checked={settings.debugMode}
                onChange={(e) => handleChange('debugMode', e.target.checked)}
              />
            </SettingRow>

            <SettingRow>
              <SettingLabel
                title="Log Level"
                description="Minimum log level to display"
              />
              <select
                value={settings.logLevel}
                onChange={(e) => handleChange('logLevel', e.target.value)}
                className="input w-48"
              >
                <option value="debug">Debug</option>
                <option value="info">Info</option>
                <option value="warn">Warning</option>
                <option value="error">Error</option>
              </select>
            </SettingRow>

            <SettingRow>
              <SettingLabel
                title="WebGL Acceleration"
                description="Use GPU acceleration for charts (requires WebGL support)"
              />
              <Toggle
                checked={settings.enableWebGL}
                onChange={(e) => handleChange('enableWebGL', e.target.checked)}
              />
            </SettingRow>

            <div className="pt-4 border-t border-dark-200 dark:border-dark-700">
              <button onClick={handleResetSettings} className="btn-secondary">
                Reset All Settings to Defaults
              </button>
            </div>
          </SettingsSection>
        )}
      </div>
    </div>
  )
}

function SettingsSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-dark-900 dark:text-dark-100">{title}</h3>
      {children}
    </div>
  )
}

function SettingRow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-4 border-b border-dark-100 dark:border-dark-800 last:border-0">
      {children}
    </div>
  )
}

function SettingLabel({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex-1">
      <p className="font-medium text-dark-900 dark:text-dark-100">{title}</p>
      <p className="text-sm text-dark-500 dark:text-dark-400">{description}</p>
    </div>
  )
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (e: React.ChangeEvent<HTMLInputElement>) => void }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={(e) => onChange({ target: { checked: !checked } } as any)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
        checked ? 'bg-primary-600' : 'bg-dark-300 dark:bg-dark-600'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  )
}