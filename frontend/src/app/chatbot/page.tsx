'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { AlertCircle, MessageCircle, MoreHorizontal, Plus, Search, Menu, X } from 'lucide-react';
import { ChatInterface } from '@/components/chat';
import { createSession, deleteSession, listSessions, renameSession } from '@/lib/api/chat';
import { useAuthStore } from '@/lib/stores/authStore';
import type { ChatSession } from '@/types/chat';

export default function ChatbotPage() {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    if (isHydrated && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isHydrated, router]);

  const {
    data: sessionsResponse,
    isLoading: isLoadingSessions,
    error: sessionsError,
    refetch: refetchSessions,
  } = useQuery({
    queryKey: ['chat-sessions'],
    queryFn: () => listSessions(1, 50),
    enabled: isHydrated && isAuthenticated,
  });

  const sessions = useMemo(() => sessionsResponse?.sessions ?? [], [sessionsResponse?.sessions]);
  const currentSession = sessions.find((session) => session.id === currentSessionId) ?? sessions[0] ?? null;

  useEffect(() => {
    if (!currentSessionId && sessions.length > 0) {
      setCurrentSessionId(sessions[0].id);
    }
  }, [currentSessionId, sessions]);

  const createSessionMutation = useMutation({
    mutationFn: () => createSession({ title: 'New conversation' }),
    onSuccess: (session) => {
      setCurrentSessionId(session.id);
      refetchSessions();
    },
  });

  const filteredSessions = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return sessions;

    return sessions.filter((session) => {
      return (
        session.title.toLowerCase().includes(query) ||
        session.preview.toLowerCase().includes(query)
      );
    });
  }, [searchQuery, sessions]);

  if (!isHydrated || !isAuthenticated) {
    return null;
  }

  return (
    <div className="fixed inset-0 overflow-hidden bg-[radial-gradient(circle_at_18%_12%,rgba(0,122,255,0.10),transparent_30%),radial-gradient(circle_at_84%_20%,rgba(52,199,89,0.08),transparent_28%),linear-gradient(180deg,#f7f9fc_0%,#eef3f8_100%)] px-3 pb-4 pt-40 md:px-5 md:pt-44">
      <div className="mx-auto flex h-full min-h-0 max-w-[1360px] overflow-hidden rounded-[30px] border border-black/8 border-t-white/80 bg-white/52 shadow-[0_28px_70px_-36px_rgba(15,23,42,0.45),inset_0_1px_0_rgba(255,255,255,0.74)] backdrop-blur-3xl">
        <aside
          className={`
            fixed left-3 top-40 z-30 flex h-[calc(100svh-10.75rem)] w-[300px] flex-shrink-0 flex-col
            rounded-[28px] border border-black/8 border-t-white/80 bg-white/66 shadow-[0_24px_56px_rgba(15,23,42,0.16),inset_0_1px_0_rgba(255,255,255,0.76)] backdrop-blur-3xl
            transition-all duration-300 ease-out md:static md:z-auto md:h-full md:shadow-none
            ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
          `}
        >
          <div className="border-b border-black/5 p-3.5">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h1 className="font-sans text-[17px] font-semibold text-slate-950">Chats</h1>
                <p className="text-xs text-slate-500">Recent conversations</p>
              </div>
              <button
                type="button"
                onClick={() => createSessionMutation.mutate()}
                disabled={createSessionMutation.isPending}
                className="flex h-9 w-9 items-center justify-center rounded-full bg-[#007AFF] text-white shadow-[0_12px_24px_rgba(0,122,255,0.26)] transition-all hover:bg-[#0A84FF] active:scale-95 disabled:opacity-50"
                aria-label="Create chat"
              >
                <Plus className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>

            <label className="relative block">
              <span className="sr-only">Search conversations</span>
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
              <input
                type="search"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Search"
                className="h-10 w-full rounded-2xl border border-black/5 border-t-white/70 bg-white/62 pl-9 pr-3 text-sm text-slate-900 outline-none shadow-[inset_0_1px_0_rgba(255,255,255,0.66)] backdrop-blur-2xl transition-all placeholder:text-slate-400 focus:border-[#007AFF]/45 focus:bg-white/82 focus:ring-4 focus:ring-[#007AFF]/10"
              />
            </label>
          </div>

          <SessionRail
            sessions={filteredSessions}
            activeSessionId={currentSession?.id ?? null}
            isLoading={isLoadingSessions}
            error={sessionsError instanceof Error ? sessionsError.message : null}
            onSelectSession={setCurrentSessionId}
            onRefetch={refetchSessions}
            onSessionDeleted={(deletedId) => {
              if (currentSessionId === deletedId) {
                const next = sessions.find((s) => s.id !== deletedId);
                setCurrentSessionId(next?.id ?? null);
              }
              refetchSessions();
            }}
          />
        </aside>

        {/* Sidebar overlay backdrop on mobile */}
        {sidebarOpen && (
          <div
            className="fixed inset-x-0 bottom-0 top-36 z-20 bg-slate-950/20 backdrop-blur-sm md:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
        )}

        <main className="flex min-w-0 flex-1 flex-col overflow-hidden bg-white/24">
          <div className="flex h-14 items-center gap-3 border-b border-black/5 bg-white/55 px-4 backdrop-blur-2xl md:hidden">
            <button
              type="button"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="rounded-full p-2 text-slate-700 transition-colors hover:bg-white/70"
              aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
            >
              {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
            <span className="text-sm font-semibold text-slate-800">Chats</span>
          </div>
          {currentSession ? (
            <ChatInterface
              session={currentSession}
              onSessionUpdate={() => refetchSessions()}
              onCloseSidebar={() => setSidebarOpen(false)}
            />
          ) : (
            <EmptyChatState
              isLoading={isLoadingSessions || createSessionMutation.isPending}
              error={sessionsError instanceof Error ? sessionsError.message : null}
              onCreate={() => createSessionMutation.mutate()}
            />
          )}
        </main>
      </div>
    </div>
  );
}

function SessionRail({
  sessions,
  activeSessionId,
  isLoading,
  error,
  onSelectSession,
  onRefetch,
  onSessionDeleted,
}: {
  sessions: ChatSession[];
  activeSessionId: string | null;
  isLoading: boolean;
  error: string | null;
  onSelectSession: (sessionId: string) => void;
  onRefetch: () => void;
  onSessionDeleted: (sessionId: string) => void;
}) {
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (renamingId && renameInputRef.current) {
      renameInputRef.current.focus();
      renameInputRef.current.select();
    }
  }, [renamingId]);

  const startRename = (session: ChatSession) => {
    setMenuOpenId(null);
    setRenamingId(session.id);
    setRenameValue(session.title);
  };

  const commitRename = async (sessionId: string) => {
    const trimmed = renameValue.trim();
    if (trimmed) {
      try {
        await renameSession(sessionId, trimmed);
        onRefetch();
      } catch {
        // silent — leave the old title in place
      }
    }
    setRenamingId(null);
  };

  const handleDelete = async (session: ChatSession) => {
    setMenuOpenId(null);
    if (!window.confirm(`Delete "${session.title}"? This cannot be undone.`)) return;
    try {
      await deleteSession(session.id);
      onSessionDeleted(session.id);
    } catch {
      // silent
    }
  };

  if (isLoading) {
    return <div className="p-4 text-sm text-slate-500">Loading chats...</div>;
  }

  if (error) {
    return (
      <div className="m-4 rounded-xl border border-red-200/60 bg-red-50/60 p-3 text-sm text-red-700 backdrop-blur-sm">
        <AlertCircle className="mb-2 h-5 w-5" aria-hidden="true" />
        {error}
      </div>
    );
  }

  if (sessions.length === 0) {
    return <div className="p-4 text-sm text-slate-500">No chats yet.</div>;
  }

  return (
    <div className="scrollbar-none min-h-0 flex-1 overflow-y-auto p-2.5">
      {sessions.map((session) => {
        const isActive = activeSessionId === session.id;
        const isRenaming = renamingId === session.id;
        const menuOpen = menuOpenId === session.id;

        return (
          <div
            key={session.id}
            className={`group relative mb-1 flex items-center rounded-xl px-3 py-2 transition-all ${
              isActive
                ? 'border border-black/5 border-t-white/80 bg-white/78 text-slate-950 shadow-[0_12px_26px_rgba(15,23,42,0.08),inset_0_1px_0_rgba(255,255,255,0.72)] backdrop-blur-2xl'
                : 'text-slate-700 hover:bg-white/48'
            }`}
          >
            {/* Rename input — replaces the button while editing */}
            {isRenaming ? (
              <input
                ref={renameInputRef}
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                onBlur={() => commitRename(session.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') commitRename(session.id);
                  if (e.key === 'Escape') setRenamingId(null);
                }}
                title="Rename conversation"
                placeholder="Conversation name"
                aria-label="Rename conversation"
                className="min-w-0 flex-1 rounded-xl border border-[#007AFF]/30 bg-white/85 px-2 py-1 text-sm font-semibold text-slate-900 outline-none focus:ring-4 focus:ring-[#007AFF]/10"
              />
            ) : (
              /* Select session button */
              <button
                type="button"
                onClick={() => onSelectSession(session.id)}
                className="min-w-0 flex-1 text-left"
              >
                <span className="block truncate text-[13px] font-semibold">{session.title}</span>
                <span className="mt-0.5 block text-[11px] text-slate-500">
                  {session.message_count} messages
                </span>
              </button>
            )}

            {/* Three-dot menu button — visible on hover */}
            {!isRenaming && (
              <div className="relative ml-1 flex-shrink-0">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setMenuOpenId(menuOpen ? null : session.id);
                  }}
                  className="rounded-full p-1 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-black/5 focus:opacity-100"
                  aria-label="Session options"
                >
                  <MoreHorizontal className="h-4 w-4 text-slate-500" />
                </button>

                {menuOpen && (
                  <>
                    {/* Backdrop to close menu */}
                    <div
                      className="fixed inset-0 z-10"
                      onClick={() => setMenuOpenId(null)}
                    />
                    <div className="absolute right-0 top-full z-20 mt-1 w-36 overflow-hidden rounded-2xl border border-black/5 border-t-white/70 bg-white/82 shadow-xl backdrop-blur-2xl">
                      <button
                        type="button"
                        onClick={() => startRename(session)}
                        className="w-full px-3 py-2 text-left text-sm text-slate-700 transition-colors hover:bg-black/5"
                      >
                        Rename
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(session)}
                        className="w-full px-3 py-2 text-left text-sm text-red-600 transition-colors hover:bg-red-50/70"
                      >
                        Delete
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function EmptyChatState({
  isLoading,
  error,
  onCreate,
}: {
  isLoading: boolean;
  error: string | null;
  onCreate: () => void;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-5 bg-transparent p-6 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-[22px] border border-black/5 border-t-white/70 bg-white/70 text-[#007AFF] shadow-[inset_0_1px_0_rgba(255,255,255,0.74),0_18px_42px_rgba(15,23,42,0.1)] backdrop-blur-2xl">
        <MessageCircle className="h-7 w-7" aria-hidden="true" />
      </div>
      <div>
        <h2 className="font-sans text-2xl font-semibold text-slate-950">Start a chat</h2>
        <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">
          Ask about the article corpus, recent topics, or anything you want the agent to investigate.
        </p>
      </div>
      {error && <p className="max-w-md text-sm text-red-700">{error}</p>}
      <button
        type="button"
        onClick={onCreate}
        disabled={isLoading}
        className="inline-flex items-center rounded-full bg-[#007AFF] px-4 py-2 text-sm font-semibold text-white shadow-[0_12px_26px_rgba(0,122,255,0.26)] transition-all hover:bg-[#0A84FF] active:scale-95 disabled:opacity-50"
      >
        <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
        {isLoading ? 'Starting...' : 'New chat'}
      </button>
    </div>
  );
}
