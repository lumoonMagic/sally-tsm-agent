import React, { useEffect, useState } from 'react'
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent
} from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Select, SelectItem, SelectTrigger, SelectContent } from '@/components/ui/select'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Loader2, Database, Key, Settings, CheckCircle, AlertTriangle } from 'lucide-react'

// ⭐ NEW IMPORTS required by the MD file
import {
  configureDatabaseApi,
  configureLLMApi,
  getConfigStatus,
  testBackendConnection
} from '@/lib/configApi'

import { isProductionMode, getModeInfo } from '@/lib/mode'



export default function ConfigurationCockpit() {
  // ⭐ NEW STATE (As per MD instructions)
  const [mode, setMode] = useState<'demo' | 'production'>('demo')
  const [backendStatus, setBackendStatus] = useState<'idle' | 'checking' | 'online' | 'offline'>('idle')
  const [lastSavedConfig, setLastSavedConfig] = useState<any>(null)

  // Existing states retained (do not remove)
  const [databaseConfig, setDatabaseConfig] = useState({
    type: 'postgres',
    host: '',
    port: 5432,
    database: '',
    user: '',
    password: ''
  })

  const [geminiApiKey, setGeminiApiKey] = useState('')
  const [testResult, setTestResult] =
    useState<'idle' | 'testing' | 'success' | 'error'>('idle')



  // ---------------------------------------------------------
  // ⭐ NEW useEffect → Detect mode + Check backend status
  // ---------------------------------------------------------
  useEffect(() => {
    const info = getModeInfo()
    setMode(info.mode)

    setBackendStatus('checking')
    testBackendConnection()
      .then((ok) => setBackendStatus(ok ? 'online' : 'offline'))
      .catch(() => setBackendStatus('offline'))
  }, [])



  // ---------------------------------------------------------
  // ⭐ NEW — Save database config to backend via configApi
  // ---------------------------------------------------------
  const handleDatabaseSave = async () => {
    try {
      const saved = await configureDatabaseApi(databaseConfig)
      setLastSavedConfig(saved)
      alert('Database configuration saved!')
    } catch (err) {
      console.error(err)
      alert('Failed to save database configuration.')
    }
  }



  // ---------------------------------------------------------
  // ⭐ NEW — Save LLM key to backend via configApi
  // ---------------------------------------------------------
  const handleLLMSave = async () => {
    try {
      const saved = await configureLLMApi({ geminiApiKey })
      setLastSavedConfig(saved)
      alert('LLM config saved!')
    } catch (err) {
      console.error(err)
      alert('Failed to save LLM configuration.')
    }
  }



  // ---------------------------------------------------------
  // UPDATED testConnection — call backend test API
  // ---------------------------------------------------------
  const testConnection = async () => {
    try {
      setTestResult('testing')
      const resp = await testBackendConnection(databaseConfig)
      setTestResult(resp ? 'success' : 'error')
    } catch (err) {
      console.error(err)
      setTestResult('error')
    }
  }



  return (
    <div className="space-y-6">
      {/* =========================================== */}
      {/*            SYSTEM STATUS PANEL              */}
      {/* =========================================== */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings size={18} />
            System Status
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-2">
          <div className="text-sm">
            <strong>Mode:</strong>{' '}
            {mode === 'demo' ? 'Demo Mode (IndexedDB)' : 'Production Mode (Backend Enabled)' }
          </div>

          <div className="text-sm flex items-center gap-2">
            <strong>Backend:</strong>
            {backendStatus === 'checking' && (
              <span className="flex items-center gap-2 text-blue-500">
                <Loader2 className="animate-spin" size={14} /> Checking...
              </span>
            )}

            {backendStatus === 'online' && (
              <span className="flex items-center gap-2 text-green-600">
                <CheckCircle size={14} /> Online
              </span>
            )}

            {backendStatus === 'offline' && (
              <span className="flex items-center gap-2 text-red-600">
                <AlertTriangle size={14} /> Offline
              </span>
            )}
          </div>

          {lastSavedConfig && (
            <div className="text-xs text-gray-500">
              <strong>Last Saved:</strong> {JSON.stringify(lastSavedConfig)}
            </div>
          )}
        </CardContent>
      </Card>



      {/* =========================================== */}
      {/*              TABS (unchanged)               */}
      {/* =========================================== */}
      <Tabs defaultValue="database" className="w-full">
        <TabsList className="grid grid-cols-3">
          <TabsTrigger value="database">Database</TabsTrigger>
          <TabsTrigger value="llm">LLM</TabsTrigger>
          <TabsTrigger value="system">System</TabsTrigger>
        </TabsList>



        {/* ================================================= */}
        {/*               DATABASE TAB (updated)              */}
        {/* ================================================= */}
        <TabsContent value="database">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database size={18} />
                Database Configuration
              </CardTitle>
            </CardHeader>

            <CardContent className="space-y-3">
              {/* DB Type */}
              <Select
                value={databaseConfig.type}
                onValueChange={(v) => setDatabaseConfig({ ...databaseConfig, type: v })}
              >
                <SelectTrigger>Database Type</SelectTrigger>
                <SelectContent>
                  <SelectItem value="postgres">PostgreSQL</SelectItem>
                  <SelectItem value="mysql">MySQL</SelectItem>
                  <SelectItem value="sqlite">SQLite</SelectItem>
                  <SelectItem value="mongodb">MongoDB</SelectItem>
                  <SelectItem value="oracle">Oracle</SelectItem>
                </SelectContent>
              </Select>

              {/* Host */}
              <Input
                placeholder="Host"
                value={databaseConfig.host}
                onChange={(e) =>
                  setDatabaseConfig({ ...databaseConfig, host: e.target.value })
                }
              />

              {/* Port */}
              <Input
                type="number"
                placeholder="Port"
                value={databaseConfig.port}
                onChange={(e) =>
                  setDatabaseConfig({ ...databaseConfig, port: Number(e.target.value) })
                }
              />

              {/* DB Name */}
              <Input
                placeholder="Database Name"
                value={databaseConfig.database}
                onChange={(e) =>
                  setDatabaseConfig({ ...databaseConfig, database: e.target.value })
                }
              />

              {/* User */}
              <Input
                placeholder="User"
                value={databaseConfig.user}
                onChange={(e) =>
                  setDatabaseConfig({ ...databaseConfig, user: e.target.value })
                }
              />

              {/* Password */}
              <Input
                placeholder="Password"
                type="password"
                value={databaseConfig.password}
                onChange={(e) =>
                  setDatabaseConfig({ ...databaseConfig, password: e.target.value })
                }
              />

              {/* BUTTONS */}
              <div className="flex gap-3 pt-2">
                <Button onClick={testConnection} variant="secondary">
                  {testResult === 'testing' && (
                    <Loader2 size={16} className="animate-spin mr-2" />
                  )}
                  Test Connection
                </Button>

                <Button onClick={handleDatabaseSave}>Save Configuration</Button>
              </div>

              {/* Test Results */}
              {testResult === 'success' && (
                <p className="text-green-600 flex items-center gap-2">
                  <CheckCircle size={14} /> Connection successful.
                </p>
              )}
              {testResult === 'error' && (
                <p className="text-red-600 flex items-center gap-2">
                  <AlertTriangle size={14} /> Connection failed.
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>



        {/* ================================================= */}
        {/*                  LLM TAB (updated)                */}
        {/* ================================================= */}
        <TabsContent value="llm">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key size={18} />
                LLM / Gemini Configuration
              </CardTitle>
            </CardHeader>

            <CardContent className="space-y-3">
              <Input
                type="password"
                placeholder="Enter Gemini API Key"
                value={geminiApiKey}
                onChange={(e) => setGeminiApiKey(e.target.value)}
              />

              <Button onClick={handleLLMSave}>Save API Key</Button>
            </CardContent>
          </Card>
        </TabsContent>



        {/* ================================================= */}
        {/*               SYSTEM TAB (unchanged)              */}
        {/* ================================================= */}
        <TabsContent value="system">
          <Card>
            <CardHeader>
              <CardTitle>System Settings</CardTitle>
            </CardHeader>
            <CardContent>Coming soon</CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
