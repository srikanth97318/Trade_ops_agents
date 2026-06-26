import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ShieldAlert, Activity, Clock, Server, Zap, BrainCircuit,
  AlertTriangle, CheckCircle2, ChevronRight, BarChart3,
  FileText, GitBranch, Gauge, Eye, BookOpen, Radio,
  DollarSign, Terminal, ArrowRight, Database, Cpu, Layers,
  RefreshCw, TrendingUp, Play
} from 'lucide-react'

// ─── Types ─────────────────────────────────────────────────────────────
interface AgentInsight {
  agent_name: string
  analysis: string
  confidence: number
  data_points: string[] | null
}

interface IncidentReport {
  incident_id: string
  incident_summary: string
  probable_root_cause: string
  blast_radius: string[]
  blast_radius_narration: string
  timeline: string[]
  recommended_actions: string[]
  confidence_score: number
  explainability: string
  agent_insights: AgentInsight[]
  severity: string
  status: string
  estimated_revenue_impact: number
  evidence: string[]
  next_investigation_steps: string[]
}

interface Scenario {
  id: string
  name: string
  severity: 'critical' | 'warning'
  service: string
  desc: string
  icon: any
}

// ─── Sample Scenario Metadata ──────────────────────────────────────────
const SCENARIOS: Scenario[] = [
  { id: 'db_outage', name: 'Database Outage', severity: 'critical', service: 'user-db', desc: 'Replica set unreachable timeout', icon: Database },
  { id: 'redis_failure', name: 'Redis Cache Failure', severity: 'critical', service: 'redis-cache', desc: 'Redis OOM eviction failure', icon: Cpu },
  { id: 'memory_leak', name: 'Memory Leak', severity: 'warning', service: 'auth-service', desc: 'JVM RSS memory drifting upward', icon: BarChart3 },
  { id: 'pod_crash', name: 'Kubernetes Pod Crash', severity: 'critical', service: 'orders-service', desc: 'orders-service CrashLoopBackOff', icon: Server },
  { id: 'bad_deployment', name: 'Bad Deployment', severity: 'critical', service: 'checkout-api', desc: 'HTTP 500 spike after release v2.4.1', icon: Layers },
  { id: 'external_api', name: 'External API Outage', severity: 'critical', service: 'payments-service', desc: 'Stripe API checkout connection refuse', icon: Zap },
  { id: 'high_latency', name: 'High Latency Spike', severity: 'warning', service: 'api-gateway', desc: 'API Gateway p99 latency > 3500ms', icon: Clock },
]

// ─── Node Topology Map for SVG Graph ───────────────────────────────────
interface GraphNode {
  id: string
  label: string
  x: number
  y: number
  type: 'gateway' | 'service' | 'db' | 'external'
}

const GRAPH_NODES: GraphNode[] = [
  { id: 'load-balancer', label: 'Load Balancer', x: 60, y: 150, type: 'gateway' },
  { id: 'api-gateway', label: 'API Gateway', x: 180, y: 150, type: 'gateway' },
  // Microservices
  { id: 'auth-service', label: 'Auth Svc', x: 320, y: 60, type: 'service' },
  { id: 'orders-service', label: 'Orders Svc', x: 320, y: 140, type: 'service' },
  { id: 'payments-service', label: 'Payments Svc', x: 320, y: 220, type: 'service' },
  { id: 'checkout-api', label: 'Checkout API', x: 320, y: 300, type: 'service' },
  // Datastores & External
  { id: 'redis-cache', label: 'Redis Cache', x: 480, y: 60, type: 'db' },
  { id: 'user-db', label: 'User DB', x: 480, y: 140, type: 'db' },
  { id: 'stripe-api', label: 'Stripe API', x: 480, y: 220, type: 'external' },
  { id: 'product-db', label: 'Product DB', x: 480, y: 300, type: 'db' },
]

const GRAPH_EDGES = [
  { from: 'load-balancer', to: 'api-gateway' },
  { from: 'api-gateway', to: 'auth-service' },
  { from: 'api-gateway', to: 'orders-service' },
  { from: 'api-gateway', to: 'checkout-api' },
  { from: 'checkout-api', to: 'orders-service' },
  { from: 'checkout-api', to: 'payments-service' },
  { from: 'auth-service', to: 'user-db' },
  { from: 'auth-service', to: 'redis-cache' },
  { from: 'orders-service', to: 'user-db' },
  { from: 'orders-service', to: 'redis-cache' },
  { from: 'payments-service', to: 'user-db' },
  { from: 'payments-service', to: 'stripe-api' },
  { from: 'checkout-api', to: 'product-db' },
]

const agentIcons: Record<string, any> = {
  'Logs Agent': FileText,
  'Metrics Agent': BarChart3,
  'Dependency Agent': GitBranch,
  'Timeline Agent': Clock,
  'Runbook Agent': BookOpen,
  'Coordinator Agent': BrainCircuit,
}

const agentColors: Record<string, string> = {
  'Logs Agent': 'text-cyan-400',
  'Metrics Agent': 'text-purple-400',
  'Dependency Agent': 'text-amber-400',
  'Timeline Agent': 'text-blue-400',
  'Runbook Agent': 'text-green-400',
  'Coordinator Agent': 'text-rose-400',
}

export default function App() {
  const [selectedScenario, setSelectedScenario] = useState<string>('db_outage')
  const [report, setReport] = useState<IncidentReport | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [activeAgent, setActiveAgent] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'commander' | 'metrics' | 'logs' | 'graph'>('commander')
  const [systemAlerts, setSystemAlerts] = useState<any[]>([])

  // Load first demo report on mount
  useEffect(() => {
    fetchIncidentReport('db_outage', false)
  }, [])

  const fetchIncidentReport = async (scenarioId: string, runSimulationAnim: boolean) => {
    setError(null)
    setSelectedScenario(scenarioId)
    
    if (runSimulationAnim) {
      setIsAnalyzing(true)
      setReport(null)
      const agents = ['Logs Agent', 'Metrics Agent', 'Dependency Agent', 'Timeline Agent', 'Runbook Agent', 'Coordinator Agent']
      for (const agent of agents) {
        setActiveAgent(agent)
        await new Promise(r => setTimeout(r, 600))
      }
    }

    try {
      const res = await fetch(`/api/alerts/demo?scenario=${scenarioId}`)
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`)
      }
      const data = await res.json()
      setReport(data)
      // Add to incident list
      setSystemAlerts(prev => {
        const exists = prev.some(item => item.incident_id === data.incident_id)
        if (exists) return prev
        return [data, ...prev].slice(0, 10)
      })
    } catch (err: any) {
      console.error(err)
      setError('Backend API is not reachable. Ensure the FastAPI backend is running on port 8080.')
    } finally {
      setIsAnalyzing(false)
      setActiveAgent(null)
    }
  }

  // Get current alert details from the scenario
  const currentScenarioMeta = SCENARIOS.find(s => s.id === selectedScenario)
  
  // Extract metrics from report
  const getMetricsData = () => {
    if (!report || !report.agent_insights) return []
    const metricsInsight = report.agent_insights.find(ai => ai.agent_name === 'Metrics Agent')
    return metricsInsight?.data_points || []
  }

  // Extract logs from report
  const getLogsData = () => {
    if (!report || !report.agent_insights) return []
    const logsInsight = report.agent_insights.find(ai => ai.agent_name === 'Logs Agent')
    return logsInsight?.data_points || []
  }

  return (
    <div className="min-h-screen bg-bg text-gray-100 flex flex-col font-sans selection:bg-accent-purple/30 selection:text-white">
      {/* ─── Header ─────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 bg-bg-card/80 backdrop-blur-xl border-b border-white/5 shadow-lg">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-blue via-accent-purple to-accent-cyan flex items-center justify-center shadow-lg shadow-accent-purple/20">
              <BrainCircuit size={22} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">
                TradeSage <span className="gradient-text">Ops</span>
              </h1>
              <p className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider">AI Incident Commander</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-2 bg-white/[0.02] border border-white/5 px-3 py-1.5 rounded-lg text-xs text-gray-400">
              <span className="w-2 h-2 rounded-full bg-accent-green animate-pulse" />
              <span>Multi-Agent SRE Pipeline: Active</span>
            </div>
            <button
              onClick={() => fetchIncidentReport(selectedScenario, true)}
              disabled={isAnalyzing}
              className="flex items-center gap-2 bg-gradient-to-r from-accent-red to-rose-600 hover:from-rose-600 hover:to-rose-700 text-white px-4 py-2 rounded-lg font-semibold text-xs transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-accent-red/20 active:scale-95"
            >
              <Zap size={14} />
              {isAnalyzing ? 'Analyzing Alert...' : 'Simulate Selected Alert'}
            </button>
          </div>
        </div>
      </header>

      {/* ─── Dashboard Body ─────────────────────────────────────── */}
      <div className="flex-1 max-w-7xl w-full mx-auto px-6 py-6 grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* ─── Column 1: Incident Feed (Left) ───────────────────── */}
        <div className="space-y-6 lg:col-span-1">
          <div className="glass rounded-xl p-4">
            <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Layers size={14} className="text-accent-blue" />
              Incident Feed
            </h2>
            
            <div className="space-y-2">
              {SCENARIOS.map((sc) => {
                const isSelected = selectedScenario === sc.id
                return (
                  <button
                    key={sc.id}
                    onClick={() => fetchIncidentReport(sc.id, true)}
                    disabled={isAnalyzing}
                    className={`w-full text-left p-3 rounded-lg border transition-all flex flex-col gap-1.5 ${
                      isSelected
                        ? 'bg-accent-blue/10 border-accent-blue/40 shadow-inner'
                        : 'bg-white/[0.02] border-white/5 hover:bg-white/[0.04] hover:border-white/10'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <sc.icon size={14} className={isSelected ? 'text-accent-blue' : 'text-gray-400'} />
                        <span className="font-semibold text-xs">{sc.name}</span>
                      </div>
                      <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono uppercase ${
                        sc.severity === 'critical' ? 'bg-red-950 text-red-400 border border-red-900/30' : 'bg-amber-950 text-amber-400 border border-amber-900/30'
                      }`}>
                        {sc.severity}
                      </span>
                    </div>
                    <span className="text-[10px] text-gray-500 line-clamp-1">{sc.desc}</span>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="glass rounded-xl p-4 bg-gradient-to-b from-bg-card to-bg-card/30">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center justify-between">
              <span>Topology Health</span>
              <RefreshCw size={10} className="text-gray-500 animate-spin-slow cursor-pointer" />
            </h3>
            <div className="space-y-2 text-xs">
              {GRAPH_NODES.map((node) => {
                const isFailed = report && node.id === report.probable_root_cause.split("'")[1] || node.id === currentScenarioMeta?.service
                const isAffected = report && report.blast_radius.includes(node.id)
                return (
                  <div key={node.id} className="flex items-center justify-between py-1 border-b border-white/[0.02]">
                    <span className="text-gray-400 font-mono text-[11px]">{node.label}</span>
                    <span className={`flex items-center gap-1 text-[10px] ${
                      isFailed ? 'text-red-400 font-semibold' : isAffected ? 'text-amber-400' : 'text-green-500'
                    }`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${
                        isFailed ? 'bg-red-500 animate-ping' : isAffected ? 'bg-amber-500' : 'bg-green-500'
                      }`} />
                      {isFailed ? 'CRITICAL' : isAffected ? 'DEGRADED' : 'HEALTHY'}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* ─── Column 2 & 3: Main Dashboard Content (Center) ────── */}
        <div className="lg:col-span-2 space-y-6 flex flex-col">
          {/* Dashboard Section Selection Tabs */}
          <div className="flex border-b border-white/5 gap-2">
            {[
              { id: 'commander', name: 'Commander Brief', icon: BrainCircuit },
              { id: 'metrics', name: 'Metrics Analysis', icon: BarChart3 },
              { id: 'logs', name: 'Log Inspector', icon: FileText },
              { id: 'graph', name: 'Blast Radius Graph', icon: GitBranch }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-1.5 px-4 py-2 border-b-2 text-xs font-semibold transition-all ${
                  activeTab === tab.id
                    ? 'border-accent-blue text-accent-blue bg-accent-blue/5'
                    : 'border-transparent text-gray-400 hover:text-gray-200'
                }`}
              >
                <tab.icon size={13} />
                {tab.name}
              </button>
            ))}
          </div>

          <div className="flex-1 min-h-[450px]">
            {/* ─── Loader State ─── */}
            <AnimatePresence mode="wait">
              {isAnalyzing && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0 }}
                  className="bg-bg-card border border-white/5 rounded-xl p-8 flex flex-col items-center justify-center h-full text-center"
                >
                  <BrainCircuit size={48} className="text-accent-blue animate-pulse mb-4" />
                  <h3 className="text-lg font-bold">Initiating Multi-Agent Investigation</h3>
                  <p className="text-xs text-gray-500 max-w-sm mt-1 mb-8">
                    TradeSage Ops is routing telemetry to specialist SRE agents. Reconstructing event graph...
                  </p>
                  
                  <div className="space-y-2 w-full max-w-xs text-left">
                    {['Logs Agent', 'Metrics Agent', 'Dependency Agent', 'Timeline Agent', 'Runbook Agent', 'Coordinator Agent'].map(name => {
                      const isActive = activeAgent === name
                      const isPast = activeAgent ? ['Logs Agent', 'Metrics Agent', 'Dependency Agent', 'Timeline Agent', 'Runbook Agent', 'Coordinator Agent'].indexOf(name) < ['Logs Agent', 'Metrics Agent', 'Dependency Agent', 'Timeline Agent', 'Runbook Agent', 'Coordinator Agent'].indexOf(activeAgent) : false
                      return (
                        <div
                          key={name}
                          className={`flex items-center justify-between p-2 rounded-lg border text-xs ${
                            isActive ? 'border-accent-blue/40 bg-accent-blue/5 text-accent-blue' : isPast ? 'border-accent-green/20 bg-accent-green/5 text-accent-green' : 'border-white/5 text-gray-600'
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            {isActive ? <Radio size={12} className="animate-pulse" /> : <CheckCircle2 size={12} />}
                            <span className="font-mono">{name}</span>
                          </div>
                          <span>{isPast ? 'COMPLETED' : isActive ? 'ANALYZING...' : 'QUEUED'}</span>
                        </div>
                      )
                    })}
                  </div>
                </motion.div>
              )}

              {/* ─── Error State ─── */}
              {error && !isAnalyzing && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass rounded-xl p-8 text-center h-full flex flex-col justify-center items-center">
                  <AlertTriangle size={36} className="text-accent-red mb-3" />
                  <p className="text-gray-300 font-semibold text-sm">{error}</p>
                  <p className="text-[10px] text-gray-500 mt-2">
                    Make sure to run your backend locally using: <code className="bg-white/5 px-2 py-0.5 rounded text-red-400 font-mono">uvicorn main:app --reload</code>
                  </p>
                </motion.div>
              )}

              {/* ─── Tab Content ─── */}
              {report && !isAnalyzing && !error && (
                <motion.div
                  key={activeTab}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                  className="space-y-6"
                >
                  {/* Tab 1: Commander Brief */}
                  {activeTab === 'commander' && (
                    <div className="space-y-6">
                      {/* Summary Brief */}
                      <div className="glass rounded-xl p-5 border-l-4 border-l-accent-red">
                        <div className="flex items-center justify-between mb-3">
                          <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
                            <ShieldAlert size={14} className="text-accent-red" />
                            Incident Summary
                          </h3>
                          <span className="text-[10px] text-gray-500 font-mono">Incident ID: {report.incident_id}</span>
                        </div>
                        <p className="text-sm text-gray-300 leading-relaxed font-mono">{report.incident_summary}</p>
                      </div>

                      {/* Root Cause Card */}
                      <div className="glass rounded-xl p-5">
                        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                          <Activity size={14} className="text-accent-purple" />
                          Probable Root Cause
                        </h3>
                        <div className="bg-red-950/10 border border-red-500/20 p-4 rounded-lg text-red-300 font-semibold text-sm mb-4 leading-relaxed font-mono">
                          {report.probable_root_cause}
                        </div>
                        
                        <div className="flex items-start gap-2 bg-white/[0.01] border border-white/5 p-3 rounded-lg text-xs">
                          <Eye size={14} className="text-accent-blue mt-0.5 flex-shrink-0" />
                          <div>
                            <span className="text-gray-400 font-semibold">Explainability: </span>
                            <span className="text-gray-500">{report.explainability}</span>
                          </div>
                        </div>
                      </div>

                      {/* Evidence Card */}
                      <div className="glass rounded-xl p-5">
                        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                          <Terminal size={14} className="text-accent-cyan" />
                          Supporting Evidence ({report.evidence.length})
                        </h3>
                        <div className="space-y-2">
                          {report.evidence.map((ev, i) => (
                            <div key={i} className="flex gap-2.5 items-start bg-white/[0.02] border border-white/5 px-3.5 py-2.5 rounded-lg text-xs font-mono">
                              <span className="w-1.5 h-1.5 rounded-full bg-accent-cyan mt-1.5 flex-shrink-0" />
                              <span className="text-gray-300">{ev}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Tab 2: Metrics */}
                  {activeTab === 'metrics' && (
                    <div className="space-y-6">
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                        {/* Interactive Metrics Cards */}
                        {getMetricsData().map((m, index) => {
                          const [name, valStr] = m.split(': ')
                          const value = parseFloat(valStr) || 0
                          const isWarning = value > 70 && value < 90
                          const isCritical = value >= 90
                          
                          // Generate mock historical values for sparkline
                          const points = Array.from({ length: 12 }, (_, i) => {
                            const base = value * 0.7 + Math.random() * (value * 0.3)
                            return `${i * 12},${40 - (base / 100) * 35}`
                          }).join(' ')

                          return (
                            <div key={index} className="glass rounded-xl p-4 flex flex-col justify-between h-28 border-white/5">
                              <div className="flex justify-between items-start">
                                <span className="text-[10px] text-gray-500 uppercase font-mono tracking-wider">{name.replace('_percent', '').replace('_ms', '').replace('_rps', '')}</span>
                                <span className={`w-2 h-2 rounded-full ${isCritical ? 'bg-accent-red animate-ping' : isWarning ? 'bg-accent-amber' : 'bg-accent-green'}`} />
                              </div>
                              <div className="flex items-baseline justify-between mt-1">
                                <span className="text-lg font-bold font-mono text-gray-100">{valStr}</span>
                              </div>
                              {/* Sparkline Chart */}
                              <svg className="w-full h-8 mt-2 overflow-visible" stroke={isCritical ? '#ef4444' : isWarning ? '#f59e0b' : '#10b981'} strokeWidth="1.5" fill="none">
                                <polyline points={points} />
                              </svg>
                            </div>
                          )
                        })}
                      </div>

                      <div className="glass rounded-xl p-5">
                        <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Metrics Agent Synthesis</h4>
                        <p className="text-xs font-mono text-gray-300 leading-relaxed">
                          {report.agent_insights.find(ai => ai.agent_name === 'Metrics Agent')?.analysis}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Tab 3: Logs */}
                  {activeTab === 'logs' && (
                    <div className="space-y-6">
                      <div className="bg-gray-950 border border-white/5 rounded-xl overflow-hidden shadow-2xl">
                        <div className="bg-white/[0.02] border-b border-white/5 px-4 py-2 flex items-center justify-between text-xs text-gray-500">
                          <span className="font-mono flex items-center gap-1.5"><Terminal size={12} /> syslog-analyzer.sh</span>
                          <span>UTF-8</span>
                        </div>
                        <div className="p-4 font-mono text-xs overflow-y-auto max-h-[350px] space-y-1.5">
                          {getLogsData().map((line, i) => {
                            const isError = line.toUpperCase().includes('ERROR') || line.toUpperCase().includes('FATAL') || line.toUpperCase().includes('FAIL')
                            const isWarn = line.toUpperCase().includes('WARN')
                            return (
                              <div key={i} className={`flex gap-3 hover:bg-white/[0.02] py-0.5 px-1 rounded transition-colors ${isError ? 'text-red-400 bg-red-950/10' : isWarn ? 'text-amber-400' : 'text-gray-400'}`}>
                                <span className="text-[10px] text-gray-600 select-none w-5 text-right">{i+1}</span>
                                <span className="flex-1 break-all">{line}</span>
                              </div>
                            )
                          })}
                        </div>
                      </div>

                      <div className="glass rounded-xl p-5">
                        <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Logs Agent Synthesis</h4>
                        <p className="text-xs font-mono text-gray-300 leading-relaxed">
                          {report.agent_insights.find(ai => ai.agent_name === 'Logs Agent')?.analysis}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Tab 4: Dependency Graph */}
                  {activeTab === 'graph' && (
                    <div className="space-y-6">
                      <div className="glass rounded-xl p-4 bg-gray-950/20 flex justify-center overflow-x-auto">
                        {/* SVG System Topology Graph */}
                        <svg width="560" height="360" className="overflow-visible select-none flex-shrink-0">
                          <defs>
                            <marker id="arrow" viewBox="0 0 10 10" refX="15" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                              <path d="M 0 1 L 10 5 L 0 9 z" fill="#334155" />
                            </marker>
                            <marker id="arrow-red" viewBox="0 0 10 10" refX="15" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                              <path d="M 0 1 L 10 5 L 0 9 z" fill="#ef4444" />
                            </marker>
                          </defs>

                          {/* Connections */}
                          {GRAPH_EDGES.map((edge, index) => {
                            const fromNode = GRAPH_NODES.find(n => n.id === edge.from)!
                            const toNode = GRAPH_NODES.find(n => n.id === edge.to)!
                            
                            const isFromFailed = report.probable_root_cause.toLowerCase().includes(edge.from)
                            const isToFailed = report.probable_root_cause.toLowerCase().includes(edge.to)
                            
                            const isFromAffected = report.blast_radius.includes(edge.from)
                            const isToAffected = report.blast_radius.includes(edge.to)
                            
                            const isRedPath = (isFromFailed || isFromAffected) && (isToFailed || isToAffected)

                            return (
                              <line
                                key={index}
                                x1={fromNode.x}
                                y1={fromNode.y}
                                x2={toNode.x}
                                y2={toNode.y}
                                stroke={isRedPath ? '#ef4444' : '#334155'}
                                strokeWidth={isRedPath ? '1.5' : '1'}
                                strokeDasharray={isRedPath ? '3 3' : 'none'}
                                className={isRedPath ? 'animate-pulse' : ''}
                                markerEnd={isRedPath ? 'url(#arrow-red)' : 'url(#arrow)'}
                              />
                            )
                          })}

                          {/* Service Nodes */}
                          {GRAPH_NODES.map((node) => {
                            const isRootCause = report.probable_root_cause.toLowerCase().includes(node.id) || currentScenarioMeta?.service === node.id
                            const isBlastRadius = report.blast_radius.includes(node.id)
                            
                            return (
                              <g key={node.id} className="cursor-pointer">
                                {isRootCause && (
                                  <circle
                                    cx={node.x}
                                    cy={node.y}
                                    r="22"
                                    className="fill-red-950/20 stroke-red-500 stroke-[1.5] animate-ping"
                                  />
                                )}
                                <circle
                                  cx={node.x}
                                  cy={node.y}
                                  r="16"
                                  className={`${
                                    isRootCause
                                      ? 'fill-red-950 stroke-red-500 stroke-2'
                                      : isBlastRadius
                                      ? 'fill-amber-950/80 stroke-amber-500 stroke-2'
                                      : 'fill-slate-900 stroke-slate-700 stroke-1'
                                  }`}
                                />
                                <text
                                  x={node.x}
                                  y={node.y + 26}
                                  textAnchor="middle"
                                  className="text-[9px] font-semibold font-mono fill-gray-400"
                                >
                                  {node.label}
                                </text>
                                {/* Mini Status indicator dot */}
                                <circle
                                  cx={node.x + 10}
                                  cy={node.y - 10}
                                  r="3"
                                  className={isRootCause ? 'fill-red-500' : isBlastRadius ? 'fill-amber-500' : 'fill-green-500'}
                                />
                              </g>
                            )
                          })}
                        </svg>
                      </div>

                      <div className="glass rounded-xl p-5 border-l-4 border-l-accent-amber">
                        <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                          <AlertTriangle size={12} className="text-accent-amber" />
                          Blast Radius Summary
                        </h4>
                        <p className="text-xs font-mono text-gray-300 leading-relaxed">
                          {report.blast_radius_narration}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* ─── Runbook Plan (Appears under Tab Content in center column) ─── */}
                  <div className="glass rounded-xl p-5">
                    <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-1.5">
                      <BookOpen size={14} className="text-accent-green" />
                      Runbook Synthesizer
                    </h3>
                    <div className="space-y-3">
                      {report.recommended_actions.map((act, i) => (
                        <div key={i} className="flex gap-3 bg-white/[0.01] hover:bg-white/[0.02] border border-white/5 rounded-lg p-3 transition-all hover:border-accent-green/20">
                          <div className="w-5 h-5 rounded bg-accent-green/10 text-accent-green text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                            {i+1}
                          </div>
                          <div className="space-y-1.5 flex-1">
                            <p className="text-xs text-gray-300 font-mono">{act}</p>
                            {/* If the step looks like a command, style it like terminal */}
                            {act.includes('kubectl') || act.includes('git') || act.includes('SELECT') || act.includes('df -h') ? (
                              <div className="bg-gray-950 border border-white/5 rounded px-2.5 py-1 text-[10px] text-gray-400 font-mono select-all w-fit max-w-full truncate">
                                $ {act.split(':').pop()?.trim()}
                              </div>
                            ) : null}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* ─── Bottom Timeline visualization ─── */}
                  <div className="glass rounded-xl p-5">
                    <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-1.5">
                      <Clock size={14} className="text-accent-cyan" />
                      Incident Timeline Assembler
                    </h3>
                    
                    <div className="relative border-l border-white/10 ml-2.5 pl-6 space-y-5 py-1">
                      {report.timeline.map((evt, idx) => {
                        const isAlert = evt.includes('ALERT') || evt.includes('alert')
                        const isFirst = idx === 0
                        const isLast = idx === report.timeline.length - 1
                        
                        return (
                          <div key={idx} className="relative">
                            {/* Pulse point */}
                            <span className={`absolute -left-[30px] top-1 w-2.5 h-2.5 rounded-full ring-4 ring-bg ${
                              isAlert ? 'bg-red-500 animate-pulse ring-red-900/30' : isLast ? 'bg-accent-green' : 'bg-slate-600'
                            }`} />
                            
                            <p className="text-xs text-gray-300 font-mono leading-relaxed">{evt}</p>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* ─── Column 4: Agent Reasoning Panel (Right) ──────────── */}
        <div className="space-y-6 lg:col-span-1">
          {/* Revenue Impact summary */}
          {report && !isAnalyzing && !error && (
            <div className="glass rounded-xl p-4 bg-gradient-to-br from-red-950/20 to-bg-card border-red-900/20">
              <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider flex items-center gap-1">
                <DollarSign size={10} className="text-red-400" />
                Est. Revenue Impact
              </span>
              <div className="flex items-baseline gap-2 mt-1.5">
                <span className="text-2xl font-black text-red-400 font-mono">
                  ${report.estimated_revenue_impact.toLocaleString()}
                </span>
                <span className="text-[10px] text-gray-500 font-semibold uppercase">/ hour</span>
              </div>
              <div className="flex items-center gap-1 text-[10px] text-red-500/80 font-mono mt-2">
                <TrendingUp size={10} />
                <span>Cascading user degradation detected</span>
              </div>
            </div>
          )}

          {/* SRE Agent Reasonings Panel */}
          <div className="glass rounded-xl p-4">
            <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-1.5">
              <BrainCircuit size={14} className="text-accent-purple" />
              Agent Reasonings
            </h2>
            
            <div className="space-y-4">
              {report && !isAnalyzing && !error ? (
                report.agent_insights.map((insight, idx) => {
                  const Icon = agentIcons[insight.agent_name] || BrainCircuit
                  const color = agentColors[insight.agent_name] || 'text-gray-400'
                  return (
                    <div key={idx} className="border-b border-white/5 pb-3 last:border-b-0 last:pb-0">
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-1.5">
                          <Icon size={13} className={color} />
                          <span className="text-[11px] font-bold font-mono">{insight.agent_name}</span>
                        </div>
                        <span className="text-[10px] text-accent-green font-mono font-semibold">{Math.round(insight.confidence * 100)}%</span>
                      </div>
                      <p className="text-[10px] text-gray-400 leading-relaxed font-mono">
                        {insight.analysis}
                      </p>
                    </div>
                  )
                })
              ) : (
                <p className="text-xs text-gray-600 italic font-mono">Waiting for incident telemetry to build pipeline reasonings...</p>
              )}
            </div>
          </div>

          {/* Next SRE Investigation steps */}
          {report && !isAnalyzing && !error && (
            <div className="glass rounded-xl p-4 bg-gradient-to-tr from-bg-card to-bg-card/40">
              <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <Activity size={12} className="text-accent-blue" />
                Next SRE Actions
              </h3>
              <div className="space-y-2">
                {report.next_investigation_steps.map((step, i) => (
                  <div key={i} className="flex gap-2 text-xs">
                    <span className="text-accent-blue font-bold font-mono select-none">{i+1}.</span>
                    <span className="text-gray-400 font-mono text-[11px]">{step}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ─── Footer ───────────────────────────────────────────── */}
      <footer className="border-t border-white/5 mt-auto bg-bg-card/40">
        <div className="max-w-7xl mx-auto px-6 py-4 flex flex-col sm:flex-row items-center justify-between text-[10px] text-gray-600 font-mono">
          <span>TradeSage Ops — AI SRE Control Center</span>
          <span>Powered by Google Cloud ADK • Gemini • Cloud Run</span>
        </div>
      </footer>
    </div>
  )
}
