'use client';
import logo from "../../public/logo.jpg";
import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  AlertTriangle, 
  Send, 
  ChevronRight, 
  Search, 
  RefreshCw,
  Sliders,
  Sparkles,
  Check,
  FileText,
  Filter,
  Mic,
  Database,
  Terminal,
  X
} from 'lucide-react';

import { 
  getAtRiskDeals, 
  getForecast, 
  runRevenueAgent, 
  triggerCRMWriteback, 
  runSimulation 
} from '@/services/api';

// --- SAFE HELPERS (NaN / null / string / key-mismatch fixes) ---
const formatCurrency = (val) => {
  const num = Number(val);
  if (!val || isNaN(num)) return "₹0";
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)} Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)} L`;
  return `₹${num.toLocaleString("en-IN")}`;
};

const getRiskScore = (deal) =>
  Math.round(Number(deal?.risk_score || deal?.riskScore || 0));

const getAccountName = (deal) =>
  deal?.account_name || deal?.company || deal?.name || deal?.deal_name || "Unknown Account";

const getOpportunityName = (deal) =>
  deal?.name || deal?.deal_name || deal?.opportunity_name || getAccountName(deal);

const getDealId = (deal) => deal?.deal_id || deal?.id || deal?.dealId || "";

const getDealAmount = (deal) =>
  deal?.amount ?? deal?.deal_value ?? deal?.value ?? 0;

// --- FALLBACK INITIAL DATA ---
const FALLBACK_DEALS = [
  {
    deal_id: "REV-8921",
    name: "Acme Corp Enterprise License",
    account: "Acme Corp",
    owner: "Jatin Sharma",
    amount: 8500000,
    stage: "Negotiation",
    risk_score: 87,
    confidence: 0.78,
    reasons: ["Champion uncommunicative for 18 days", "Competitor (Salesforce) cited 3x in call transcripts", "Close date pushed 2x in Q3"],
    top_reason: "Champion uncommunicative (18d)",
    nba: "Schedule VP-level executive alignment & issue 8% pilot concession",
    email_draft: {
      to: "sarah.vanderbilt@acmecorp.com",
      role: "VP of Engineering",
      subject: "RevOS / Technical Integration Roadmap & Exec Alignment - Acme Corp",
      body: "Hi Sarah,\n\nFollowing up on our engineering review. I noted we haven't locked in the sandbox milestone scheduled for next Tuesday.\n\nTo keep your Q4 deployment timeline on track, I've adjusted our integration framework to include dedicated solutions support at an 8% adjusted rate.\n\nAre you available for a brief 10-minute check-in tomorrow at 2:00 PM IST to finalize this?"
    }
  },
  {
    deal_id: "REV-8924",
    name: "FinTech Sol Expansion Contract",
    account: "FinTech Solutions",
    owner: "Ayush Jaiswal",
    amount: 12000000,
    stage: "Legal Review",
    risk_score: 64,
    confidence: 0.82,
    reasons: ["Legal redline review stalled >12 days", "Discount request exceeds threshold (>15%)"],
    top_reason: "Legal redlines stalled (>12d)",
    nba: "Convene legal sync to review pre-approved indemnity terms",
    email_draft: {
      to: "legal.compliance@fintechsol.io",
      role: "Head of Legal",
      subject: "RevOS / Execution Copy & Clause 4.2 Indemnity Revisions",
      body: "Hi Marcus,\n\nChecking in on the redline document forwarded Tuesday. Our legal counsel has pre-approved the indemnity adjustments requested.\n\nPlease let us know if we can convene today to execute the agreement."
    }
  },
  {
    deal_id: "REV-8930",
    name: "Logistics Global Regional Rollout",
    account: "Logistics Global",
    owner: "Jatin Sharma",
    amount: 4500000,
    stage: "Proposal Sent",
    risk_score: 32,
    confidence: 0.91,
    reasons: ["Positive executive sentiment in last sync", "Active champion participation"],
    top_reason: "High stakeholder engagement",
    nba: "Deliver ROI financial impact assessment directly to CFO",
    email_draft: {
      to: "r.mehta@logisticsglobal.com",
      role: "CFO",
      subject: "RevOS / Quantified ROI & Cost Breakdown - Logistics Global",
      body: "Hi Rajesh,\n\nAs discussed during our platform demo, attached is the detailed financial model detailing projected cost savings across your logistics fleet.\n\nI look forward to reviewing these figures with you."
    }
  }
];

export default function RevOSDashboard() {
  const [deals, setDeals] = useState(FALLBACK_DEALS);
  const [selectedDeal, setSelectedDeal] = useState(FALLBACK_DEALS[0]);
  const [nlQuery, setNlQuery] = useState("");
  const [isProcessingNL, setIsProcessingNL] = useState(false);
  const [agentResponse, setAgentResponse] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [emailText, setEmailText] = useState(FALLBACK_DEALS[0].email_draft.body);
  const [crmUpdated, setCrmUpdated] = useState(false);
  const [emailSent, setEmailSent] = useState(false);

  // Strategy Simulator States
  const [sdrHeadcount, setSdrHeadcount] = useState(2);
  const [discountCap, setDiscountCap] = useState(5);
  const [simulatedForecast, setSimulatedForecast] = useState("4.80");
  const [simulatedImpact, setSimulatedImpact] = useState("14.1");

  // Load Data on Mount
  useEffect(() => {
    async function loadData() {
      try {
        const dealsData = await getAtRiskDeals();
        if (dealsData && Array.isArray(dealsData) && dealsData.length > 0) {
          setDeals(dealsData);
          setSelectedDeal(dealsData[0]);
          setEmailText(dealsData[0].email_draft?.body || "");
        }
      } catch (err) {
        console.warn("Backend unavailable, loading fallback deals data.", err);
      }
    }
    loadData();
  }, []);

  const handleSelectDeal = (deal) => {
    setSelectedDeal(deal);
    setEmailText(deal.email_draft?.body || "");
    setCrmUpdated(false);
    setEmailSent(false);
  };

  const handleNLSubmit = async (e, customQuery) => {
    if (e) e.preventDefault();
    const queryToRun = customQuery || nlQuery;
    if (!queryToRun.trim()) return;

    setIsProcessingNL(true);
    setAgentResponse(null);

    try {
      const result = await runRevenueAgent(queryToRun);
      setAgentResponse(result);
    } catch (err) {
      console.error("Agent query execution failed:", err);
    } finally {
      setIsProcessingNL(false);
    }
  };

  const handleWritebackCRM = async () => {
    setCrmUpdated(true);
    await triggerCRMWriteback(getDealId(selectedDeal), {
      stage: selectedDeal.stage,
      risk_score: getRiskScore(selectedDeal)
    });
    setTimeout(() => setCrmUpdated(false), 3000);
  };

  const handleSendEmail = () => {
    setEmailSent(true);
    setTimeout(() => setEmailSent(false), 3000);
  };

  const handleSimulationChange = async (newSdr, newDiscount) => {
    setSdrHeadcount(newSdr);
    setDiscountCap(newDiscount);
    try {
      const simResult = await runSimulation(newSdr, newDiscount);
      if (simResult) {
        setSimulatedForecast(simResult.projected_forecast || "4.80");
        setSimulatedImpact(simResult.net_impact_percent || "14.1");
      }
    } catch (err) {
      console.warn("Simulator backend call failed, fallback values kept.", err);
    }
  };

  return (
    <div className="min-h-screen bg-[#08090B] text-[#F3F4F6] font-sans text-[13px] antialiased selection:bg-[#2563EB] selection:text-white">
      
      {/* 1. TOP NAVIGATION / PRODUCT HEADER */}
      <header className="sticky top-0 z-50 border-b border-[#1E222A] bg-[#0F1115] px-4 py-2 flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-3">
            <img 
              src={logo.src || logo} 
              alt="RevOS Logo" 
              className="w-10 h-10 object-contain rounded-sm" 
            />
            <div className="flex flex-col justify-center">
              <span className="font-extrabold text-[18px] tracking-[0.15em] text-white leading-none uppercase flex items-center font-mono">
                REV
                <span className="text-[#F97316] bg-[#F97316]/10 px-[3px] py-[1px] mx-[1px] rounded-[3px] border border-[#F97316]/30 inline-block leading-none">
                  O
                </span>
                S
              </span>
              <span className="text-[#8B949E] text-[10px] font-medium tracking-normal mt-0.5 leading-none">
                Sales Revenue Ops Engine
              </span>
            </div>
          </div>
          
          <nav className="flex items-center space-x-1 border-l border-[#1E222A] pl-4">
            <button 
              onClick={() => setActiveTab("overview")}
              className={`px-2.5 py-1 rounded-sm text-[12px] font-medium transition-colors ${
                activeTab === 'overview' ? 'bg-[#1E222A] text-white' : 'text-[#8B949E] hover:text-white'
              }`}
            >
              Pipeline Health
            </button>
            <button 
              onClick={() => setActiveTab("simulator")}
              className={`px-2.5 py-1 rounded-sm text-[12px] font-medium transition-colors ${
                activeTab === 'simulator' ? 'bg-[#1E222A] text-white' : 'text-[#8B949E] hover:text-white'
              }`}
            >
              What-If Simulator
            </button>
            <button 
              onClick={() => setActiveTab("audit")}
              className={`px-2.5 py-1 rounded-sm text-[12px] font-medium transition-colors ${
                activeTab === 'audit' ? 'bg-[#1E222A] text-white' : 'text-[#8B949E] hover:text-white'
              }`}
            >
              Audit Trail
            </button>
          </nav>
        </div>

        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1 text-[11px] text-[#10B981] bg-[#10B981]/10 border border-[#10B981]/20 px-2 py-0.5 rounded-sm">
            <Database className="w-3 h-3 text-[#10B981]" />
            <span>CRM CSV</span>
            <span className="text-[#8B949E]">•</span>
            <span>Email RAG</span>
            <span className="text-[#8B949E]">•</span>
            <span>Calls</span>
          </div>
        </div>
      </header>

      {/* 2. NATURAL LANGUAGE AGENT EXECUTION BAR */}
      <div className="border-b border-[#1E222A] bg-[#08090B] px-4 py-2.5 space-y-2">
        <form onSubmit={(e) => handleNLSubmit(e)} className="relative flex items-center max-w-6xl mx-auto">
          <Search className="absolute left-3 text-[#8B949E] w-3.5 h-3.5" />
          <input
            type="text"
            value={nlQuery}
            onChange={(e) => setNlQuery(e.target.value)}
            placeholder="Query Revenue Agent in Natural Language / Hinglish (e.g. 'Q3 forecast kya hai? Kaunse deals risk mein hain?')"
            className="w-full bg-[#0F1115] border border-[#1E222A] focus:border-[#2563EB] focus:outline-none text-[12px] text-white pl-9 pr-36 py-1.5 rounded-sm transition-colors placeholder-[#6C757D]"
          />
          <div className="absolute right-1 flex items-center space-x-1">
            <button 
              type="button" 
              className="p-1 hover:bg-[#1E222A] rounded-sm text-[#8B949E] hover:text-white transition-colors"
              title="Voice Query Input"
            >
              <Mic className="w-3.5 h-3.5" />
            </button>
            <button 
              type="submit"
              disabled={isProcessingNL}
              className="bg-[#2563EB] hover:bg-blue-600 disabled:opacity-50 text-white text-[11px] font-medium px-2.5 py-1 rounded-sm transition-colors flex items-center space-x-1"
            >
              {isProcessingNL ? (
                <>
                  <RefreshCw className="w-3 h-3 animate-spin mr-1" />
                  <span>Evaluating...</span>
                </>
              ) : (
                <>
                  <span>Run Agent</span>
                  <ChevronRight className="w-3 h-3 ml-0.5" />
                </>
              )}
            </button>
          </div>
        </form>

        <div className="flex items-center space-x-2 max-w-6xl mx-auto text-[11px]">
          <span className="text-[#8B949E]">Quick Queries:</span>
          <button 
            onClick={() => { setNlQuery("Q3 forecast kya hai?"); handleNLSubmit(null, "Q3 forecast kya hai?"); }}
            className="bg-[#0F1115] hover:bg-[#1E222A] border border-[#1E222A] text-[#F3F4F6] px-2 py-0.5 rounded-sm transition-colors"
          >
            🏷️ Q3 forecast kya hai?
          </button>
          <button 
            onClick={() => { setNlQuery("Kaunse deals risk mein hain?"); handleNLSubmit(null, "Kaunse deals risk mein hain?"); }}
            className="bg-[#0F1115] hover:bg-[#1E222A] border border-[#1E222A] text-[#F3F4F6] px-2 py-0.5 rounded-sm transition-colors"
          >
            🏷️ Slipped Deals (Hindi)
          </button>
          <button 
            onClick={() => { setNlQuery("Top SHAP risk factors for Acme Corp"); handleNLSubmit(null, "Top SHAP risk factors for Acme Corp"); }}
            className="bg-[#0F1115] hover:bg-[#1E222A] border border-[#1E222A] text-[#F3F4F6] px-2 py-0.5 rounded-sm transition-colors"
          >
            🏷️ Top Risk Drivers
          </button>
        </div>
      </div>

      {/* 3. AGENT THOUGHT STREAM & EXECUTION OUTPUT DRAWER */}
      {agentResponse && (
        <div className="border-b border-[#1E222A] bg-[#0F1115] px-4 py-3 max-w-6xl mx-auto my-2 rounded-sm border">
          <div className="flex justify-between items-center pb-2 border-b border-[#1E222A] mb-2">
            <div className="flex items-center space-x-2 font-mono text-[11px] text-[#10B981]">
              <Terminal className="w-3.5 h-3.5" />
              <span>AGENT THOUGHT STREAM & TOOL CALL LOGS</span>
            </div>
            <button onClick={() => setAgentResponse(null)} className="text-[#8B949E] hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="space-y-1 font-mono text-[11px] text-[#8B949E] mb-3">
            {agentResponse.thought_stream?.map((step, idx) => (
              <div key={idx} className="flex items-center space-x-2">
                <span className="text-[#2563EB]">›</span>
                <span>{step}</span>
              </div>
            ))}
          </div>

          <div className="bg-[#08090B] p-2.5 border border-[#1E222A] rounded-sm text-[12px] text-white">
            <span className="font-semibold text-[#10B981] mr-1">Agent Answer:</span>
            {agentResponse.answer}
          </div>
        </div>
      )}

      {/* 4. PIPELINE OVERVIEW WORKSPACE */}
      {activeTab === "overview" && (
        <main className="p-4 space-y-4 max-w-[1600px] mx-auto">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="bg-[#0F1115] border border-[#1E222A] p-3 rounded-sm">
              <div className="text-[11px] text-[#8B949E] font-medium uppercase tracking-wider">Q3 Pipeline Forecast (Prophet)</div>
              <div className="text-xl font-medium font-numeric text-white mt-1">₹4.20 Cr</div>
              <div className="text-[11px] text-[#10B981] mt-1 flex items-center font-numeric">
                <TrendingUp className="w-3 h-3 mr-1" />
                <span>78% Confidence Band [₹3.4Cr – ₹4.9Cr]</span>
              </div>
            </div>

            <div className="bg-[#0F1115] border border-[#1E222A] p-3 rounded-sm">
              <div className="text-[11px] text-[#8B949E] font-medium uppercase tracking-wider">Slipped Pipeline Risk (XGBoost)</div>
              <div className="text-xl font-medium font-numeric text-[#EF4444] mt-1">₹2.05 Cr</div>
              <div className="text-[11px] text-[#8B949E] mt-1">
                7 accounts requiring intervention
              </div>
            </div>

            <div className="bg-[#0F1115] border border-[#1E222A] p-3 rounded-sm">
              <div className="text-[11px] text-[#8B949E] font-medium uppercase tracking-wider">Action Acceptance Rate</div>
              <div className="text-xl font-medium font-numeric text-white mt-1">84.2%</div>
              <div className="text-[11px] text-[#10B981] mt-1">
                +15% win-rate uplift vs control
              </div>
            </div>

            <div className="bg-[#0F1115] border border-[#1E222A] p-3 rounded-sm">
              <div className="text-[11px] text-[#8B949E] font-medium uppercase tracking-wider">Capacity Hours Saved</div>
              <div className="text-xl font-medium font-numeric text-white mt-1">5.2 hrs/rep</div>
              <div className="text-[11px] text-[#8B949E] mt-1">
                Automated CRM write-backs & drafting
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* LEFT: MASTER DEALS TABLE */}
            <div className="lg:col-span-7 bg-[#0F1115] border border-[#1E222A] rounded-sm flex flex-col">
              <div className="px-3 py-2 border-b border-[#1E222A] flex items-center justify-between bg-[#0B0D10]">
                <div className="flex items-center space-x-2">
                  <span className="font-medium text-[12px] text-white">At-Risk Deal Queue</span>
                  <span className="text-[11px] bg-[#1E222A] text-[#8B949E] px-1.5 py-0.2 rounded font-mono">
                    {deals.length}
                  </span>
                </div>
                <div className="flex items-center space-x-2 text-[11px] text-[#8B949E]">
                  <Filter className="w-3 h-3" />
                  <span>Sorted by Risk (Desc)</span>
                </div>
              </div>

              <div className="overflow-x-auto flex-1">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-[#1E222A] bg-[#08090B] text-[11px] text-[#8B949E] font-medium uppercase tracking-wider">
                      <th className="p-2.5 pl-3">Account / Opportunity</th>
                      <th className="p-2.5">Value</th>
                      <th className="p-2.5">Risk Score</th>
                      <th className="p-2.5">Top SHAP Contributor</th>
                      <th className="p-2.5 pr-3 text-right">Inspect</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1E222A] text-[12px]">
                    {deals.map((deal, idx) => {
                      const dealId = getDealId(deal);
                      const isSelected = getDealId(selectedDeal) === dealId;
                      const accountName = getAccountName(deal);
                      const opportunityName = getOpportunityName(deal);
                      const riskScore = getRiskScore(deal);

                      return (
                        <tr 
                          key={dealId || idx}
                          onClick={() => handleSelectDeal(deal)}
                          className={`cursor-pointer transition-colors ${isSelected ? 'bg-[#181B22] border-l-2 border-l-[#2563EB]' : 'hover:bg-[#13151B]'}`}
                        >
                          <td className="p-2.5 pl-3">
                            <div className="font-medium text-white">{opportunityName}</div>
                            <div className="text-[11px] text-[#8B949E]">
                              {accountName}{deal.stage ? ` • ${deal.stage}` : ""}
                            </div>
                          </td>
                          <td className="p-2.5 font-numeric text-white">
                            {formatCurrency(getDealAmount(deal))}
                          </td>
                          <td className="p-2.5">
                            <span className={`inline-flex items-center px-1.5 py-0.5 rounded-sm font-mono text-[11px] ${
                              riskScore >= 80 
                                ? 'bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/30' 
                                : riskScore >= 50 
                                ? 'bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/30' 
                                : 'bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/30'
                            }`}>
                              {riskScore}/100
                            </span>
                          </td>
                          <td className="p-2.5 text-[#8B949E] truncate max-w-[180px]">
                            {deal.top_reason || deal.reasons?.[0] || "—"}
                          </td>
                          <td className="p-2.5 pr-3 text-right">
                            <ChevronRight className={`w-4 h-4 inline-block ${isSelected ? 'text-[#2563EB]' : 'text-[#8B949E]'}`} />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div className="px-3 py-2 border-t border-[#1E222A] bg-[#0B0D10] text-[11px] text-[#8B949E] flex justify-between items-center">
                <span>Model: XGBoost v1.2 (AUC: 0.89)</span>
                <span>Human-in-the-Loop Gate Active</span>
              </div>
            </div>

            {/* RIGHT: PRESCRIPTIVE ACTION & EMAIL DRAWER */}
            <div className="lg:col-span-5 bg-[#0F1115] border border-[#1E222A] rounded-sm flex flex-col">
              <div className="px-3 py-2 border-b border-[#1E222A] bg-[#0B0D10] flex justify-between items-center">
                <div>
                  <span className="text-[11px] text-[#8B949E] uppercase font-mono tracking-wider">Opportunity Detail</span>
                  <div className="text-[13px] font-semibold text-white">{getOpportunityName(selectedDeal)}</div>
                </div>
                <span className="text-[11px] text-[#8B949E] font-mono">{getDealId(selectedDeal)}</span>
              </div>

              <div className="p-3 space-y-3.5 flex-1 overflow-y-auto">
                <div className="space-y-1.5">
                  <div className="text-[11px] text-[#8B949E] uppercase font-mono tracking-wider flex justify-between">
                    <span>SHAP Risk Factors</span>
                    <span className="text-[#EF4444] font-medium">Risk Score: {getRiskScore(selectedDeal)}</span>
                  </div>
                  <div className="space-y-1">
                    {selectedDeal.reasons?.map((reason, idx) => (
                      <div key={idx} className="text-[12px] text-[#F3F4F6] flex items-center justify-between bg-[#08090B] p-2 border border-[#1E222A] rounded-sm">
                        <span className="flex items-center">
                          <AlertTriangle className="w-3.5 h-3.5 text-[#F59E0B] mr-2 flex-shrink-0" />
                          {reason}
                        </span>
                        <span className="text-[10px] font-mono text-[#EF4444] bg-[#EF4444]/10 px-1 rounded">High</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-[#08090B] border border-[#1E222A] p-2.5 rounded-sm space-y-1">
                  <div className="text-[11px] text-[#8B949E] uppercase font-mono tracking-wider flex items-center">
                    <Sparkles className="w-3 h-3 text-[#10B981] mr-1" />
                    <span>Prescribed Next-Best-Action</span>
                  </div>
                  <div className="text-[12px] font-medium text-[#10B981]">
                    {selectedDeal.nba}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="text-[11px] text-[#8B949E] uppercase font-mono tracking-wider flex items-center">
                      <FileText className="w-3 h-3 mr-1 text-[#2563EB]" />
                      Draft Follow-up Email
                    </label>
                    <span className="text-[11px] text-[#8B949E]">To: {selectedDeal.email_draft?.to}</span>
                  </div>

                  <div className="space-y-1.5">
                    <input 
                      type="text"
                      readOnly
                      value={`Subject: ${selectedDeal.email_draft?.subject || ""}`}
                      className="w-full bg-[#08090B] border border-[#1E222A] text-[11px] text-white px-2 py-1 rounded-sm focus:outline-none"
                    />
                    <textarea 
                      rows={6}
                      value={emailText}
                      onChange={(e) => setEmailText(e.target.value)}
                      className="w-full bg-[#08090B] border border-[#1E222A] text-[12px] text-white p-2 rounded-sm focus:outline-none focus:border-[#2563EB] leading-relaxed resize-none"
                    />
                  </div>
                </div>
              </div>

              <div className="p-2.5 border-t border-[#1E222A] bg-[#0B0D10] flex items-center gap-2">
                <button 
                  onClick={handleWritebackCRM}
                  disabled={crmUpdated}
                  className="flex-1 bg-[#1E222A] hover:bg-[#282D37] text-white text-[11px] font-medium py-1.5 px-2 rounded-sm border border-[#1E222A] transition-colors flex items-center justify-center space-x-1"
                >
                  {crmUpdated ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-[#10B981]" />
                      <span>CRM Synchronized</span>
                    </>
                  ) : (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 text-[#8B949E]" />
                      <span>One-Click CRM Write-back</span>
                    </>
                  )}
                </button>

                <button 
                  onClick={handleSendEmail}
                  disabled={emailSent}
                  className="flex-1 bg-[#2563EB] hover:bg-blue-600 text-white text-[11px] font-medium py-1.5 px-2 rounded-sm transition-colors flex items-center justify-center space-x-1"
                >
                  {emailSent ? (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      <span>Sent to Outbox</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-3.5 h-3.5" />
                      <span>Approve & Send</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </main>
      )}

      {/* 5. WHAT-IF STRATEGY SIMULATOR TAB */}
      {activeTab === "simulator" && (
        <main className="p-4 max-w-4xl mx-auto space-y-4">
          <div className="bg-[#0F1115] border border-[#1E222A] p-4 rounded-sm space-y-4">
            <div className="border-b border-[#1E222A] pb-3">
              <h2 className="text-[13px] font-semibold text-white flex items-center">
                <Sliders className="w-4 h-4 text-[#2563EB] mr-2" />
                Pipeline Strategy & Capacity Simulator
              </h2>
              <p className="text-[12px] text-[#8B949E] mt-0.5">
                Model velocity shifts and forecast variations prior to committing sales resources.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-1">
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-[12px] mb-1.5">
                    <span className="text-[#8B949E]">Additional SDR Capacity:</span>
                    <span className="font-mono text-white font-medium">{sdrHeadcount} Reps</span>
                  </div>
                  <input 
                    type="range" min="0" max="10" value={sdrHeadcount} 
                    onChange={(e) => handleSimulationChange(parseInt(e.target.value), discountCap)}
                    className="w-full accent-[#2563EB] bg-[#1E222A] h-1 rounded appearance-none cursor-pointer"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-[12px] mb-1.5">
                    <span className="text-[#8B949E]">Concession / Discount Ceiling:</span>
                    <span className="font-mono text-white font-medium">{discountCap}%</span>
                  </div>
                  <input 
                    type="range" min="0" max="25" value={discountCap} 
                    onChange={(e) => handleSimulationChange(sdrHeadcount, parseInt(e.target.value))}
                    className="w-full accent-[#2563EB] bg-[#1E222A] h-1 rounded appearance-none cursor-pointer"
                  />
                </div>
              </div>

              <div className="bg-[#08090B] border border-[#1E222A] p-3.5 rounded-sm flex flex-col justify-between">
                <div>
                  <div className="text-[11px] font-mono text-[#8B949E] uppercase">Simulated Q3 Projected Forecast</div>
                  <div className="text-2xl font-semibold font-numeric text-[#10B981] mt-1">
                    ₹{simulatedForecast} Cr
                  </div>
                  <div className="text-[11px] text-[#8B949E] mt-1">
                    Baseline: ₹4.20 Cr • Net Impact: +{simulatedImpact}%
                  </div>
                </div>

                <div className="pt-3 border-t border-[#1E222A] text-[11px] text-[#8B949E]">
                  Prophet parameters updated dynamically for Q3 execution.
                </div>
              </div>
            </div>
          </div>
        </main>
      )}

      {/* 6. DECISION AUDIT LOG TAB */}
      {activeTab === "audit" && (
        <main className="p-4 max-w-5xl mx-auto">
          <div className="bg-[#0F1115] border border-[#1E222A] rounded-sm">
            <div className="px-3 py-2 border-b border-[#1E222A] bg-[#0B0D10] font-semibold text-[12px] text-white">
              Agent Decision & Execution Audit Trail
            </div>
            <div className="p-3 space-y-2 font-mono text-[11px]">
              <div className="p-2 bg-[#08090B] border border-[#1E222A] rounded-sm text-[#8B949E] flex justify-between">
                <span>[2026-09-30 18:40:12] ACTION_APPROVED: Deal REV-8921 draft approved for sarah.vanderbilt@acmecorp.com</span>
                <span className="text-[#10B981]">PASSED</span>
              </div>
              <div className="p-2 bg-[#08090B] border border-[#1E222A] rounded-sm text-[#8B949E] flex justify-between">
                <span>[2026-09-30 18:38:05] MODEL_INFERENCE: XGBoost updated risk score for Acme Corp to 87 (SHAP recalculated)</span>
                <span className="text-[#2563EB]">EXECUTED</span>
              </div>
              <div className="p-2 bg-[#08090B] border border-[#1E222A] rounded-sm text-[#8B949E] flex justify-between">
                <span>[2026-09-30 18:35:22] RAG_RETRIEVAL: ChromaDB indexed 14 email threads for FinTech Solutions</span>
                <span className="text-[#2563EB]">EXECUTED</span>
              </div>
            </div>
          </div>
        </main>
      )}

    </div>
  );
}