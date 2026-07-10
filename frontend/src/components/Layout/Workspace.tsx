/* ── Main Workspace: Birth Profile → Chart + Chat ───── */

import { useState, useEffect, useCallback, type FC } from 'react';
import { get, post } from '../../api/client';
import { useAuthContext } from '../../context/AuthContext';
import { useChartContext } from '../../context/ChartContext';
import { useSSEContext } from '../../context/SSEContext';
import { useConversation } from '../../hooks/useConversation';
import ChartController, { type AnalysisScope } from '../Chart/ChartController';
import ChartDetailPanel from '../Chart/ChartDetailPanel';
import ChatPanel from '../Chat/ChatPanel';
import BirthProfileForm from '../Profile/BirthProfileForm';
import type { BirthProfile, ChartPayload, ChartCreate } from '../../types';
import { useI18n } from '../../i18n/I18nContext';

const Workspace: FC = () => {
  const { user, loading: authLoading } = useAuthContext();
  const { dispatch } = useChartContext();
  const { isConnected } = useSSEContext();
  const { t, formatDate } = useI18n();
  const {
    messages,
    sendMessage,
    updateConversation,
    sending,
    error: convError,
  } = useConversation();

  const [profileLoading, setProfileLoading] = useState(true);
  const [profile, setProfile] = useState<BirthProfile | null>(null);
  const [chartReady, setChartReady] = useState(false);
  const [chartLoading, setChartLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [natalChart, setNatalChart] = useState<ChartPayload | null>(null);
  /** Chart for selected timeline date (aspects + wheel when not on birth day) */
  const [skyChart, setSkyChart] = useState<ChartPayload | null>(null);

  useEffect(() => {
    if (authLoading || !user) return;
    const checkProfile = async () => {
      setProfileLoading(true);
      try {
        const existing = await get<BirthProfile>('/v1/me/profile');
        setProfile(existing);
      } catch {
        setProfile(null);
      } finally {
        setProfileLoading(false);
      }
    };
    checkProfile();
  }, [authLoading, user]);

  const applyNatal = useCallback(
    async (saved: BirthProfile) => {
      setChartLoading(true);
      setError(null);
      try {
        const birthTime = saved.birth_time ?? '12:00:00';
        const body: ChartCreate = {
          chart_type: 'natal',
          calculation_date: `${saved.birth_date}T${birthTime}`,
          location: {
            latitude: Number(saved.latitude),
            longitude: Number(saved.longitude),
            time_zone: saved.time_zone,
            location_name: saved.location_name ?? undefined,
          },
          house_system: saved.house_system || 'P',
        };
        const chart = await post<ChartPayload & { id: string }>('/v1/charts', body);
        setNatalChart(chart);
        setSkyChart(null);
        dispatch({ type: 'SET_CHART', payload: chart, renderMode: 'replace' });
        if (chart.id) await updateConversation({ chart_context_id: chart.id });
        setChartReady(true);
      } catch (err) {
        setError(err instanceof Error ? err.message : t('workspace.chartCalcFailed'));
      } finally {
        setChartLoading(false);
      }
    },
    [dispatch, updateConversation, t],
  );

  useEffect(() => {
    if (!profile || natalChart) return;
    applyNatal(profile);
  }, [profile, natalChart, applyNatal]);

  const handleProfileSaved = useCallback(
    async (saved: BirthProfile) => {
      setProfile(saved);
      setNatalChart(null);
      await applyNatal(saved);
    },
    [applyNatal],
  );

  const handleSend = useCallback(
    (text: string) => {
      sendMessage(text);
    },
    [sendMessage],
  );

  const handleSkyChartChange = useCallback((chart: ChartPayload | null, _date: Date) => {
    setSkyChart(chart);
  }, []);

  const handleAskAnalysis = useCallback(
    (date: Date, scope: AnalysisScope) => {
      const iso = date.toISOString().slice(0, 10);
      const monthLabel = formatDate(date, { month: 'long', year: 'numeric' });
      const year = date.getFullYear();

      let prompt: string;
      if (scope === 'day') {
        prompt = t('analysis.day', { date: iso });
      } else if (scope === 'month') {
        prompt = t('analysis.month', { month: monthLabel });
      } else {
        prompt = t('analysis.year', { year });
      }
      void sendMessage(prompt);
    },
    [sendMessage, t, formatDate],
  );

  if (authLoading || profileLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-black">
        <svg className="animate-spin h-8 w-8 text-accent/50" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    );
  }

  if (!profile || (profile && !chartReady && chartLoading)) {
    if (profile && chartLoading) {
      return (
        <div className="relative min-h-full flex items-center justify-center bg-black">
          <div className="text-center">
            <svg className="animate-spin h-10 w-10 text-accent/50 mx-auto mb-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <p className="text-zinc-500 text-sm">{t('workspace.calculatingChart')}</p>
          </div>
        </div>
      );
    }
    return <BirthProfileForm onSaved={handleProfileSaved} />;
  }

  if (error && !chartReady) {
    return (
      <div className="relative min-h-full flex items-center justify-center bg-black">
        <div className="text-center max-w-sm">
          <p className="text-red-400/80 text-sm mb-4">{error}</p>
          <button
            onClick={() => {
              setError(null);
              setProfile(null);
              setNatalChart(null);
            }}
            className="btn-primary text-xs"
          >
            {t('common.tryAgain')}
          </button>
        </div>
      </div>
    );
  }

  const aspectChart = skyChart ?? natalChart;
  const aspectTitle =
    skyChart && skyChart.chart_type !== 'natal'
      ? t('chart.skyAspects')
      : t('chart.natalAspects');

  return (
    <div className="flex flex-col md:flex-row h-full overflow-hidden bg-black">
      <div className="flex flex-1 h-full overflow-hidden min-w-0">
        {natalChart && (
          <div className="w-[clamp(320px,34vw,460px)] h-full overflow-hidden border-r border-amber-500/15 shrink-0 bg-black">
            <ChartDetailPanel
              natalChart={natalChart}
              aspectChart={aspectChart}
              aspectTitle={aspectTitle}
            />
          </div>
        )}
        <div className="flex-1 min-w-0 min-h-0 overflow-hidden bg-black">
          {natalChart && profile && (
            <ChartController
              natalChart={natalChart}
              profile={profile}
              onSkyChartChange={handleSkyChartChange}
              onAskAnalysis={handleAskAnalysis}
            />
          )}
        </div>
      </div>

      <div className="w-[clamp(280px,26vw,360px)] h-full border-l border-amber-500/15 flex flex-col shrink-0 bg-black">
        {convError && (
          <div className="text-red-400/90 text-xs px-3 py-1.5 bg-red-400/5 border-b border-red-400/10">
            {convError}
          </div>
        )}
        <ChatPanel
          messages={messages}
          onSend={handleSend}
          isStreaming={sending}
          isConnected={isConnected}
        />
      </div>
    </div>
  );
};

export default Workspace;
