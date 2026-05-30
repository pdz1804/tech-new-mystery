'use client';

import React, { useState, useMemo } from 'react';
import { Trash2, Archive, MoreVertical, Edit2, Search, ChevronDown, RotateCcw, Star } from 'lucide-react';
import type { ChatSession } from '@/types/chat';

interface SessionListProps {
  sessions: ChatSession[];
  activeSession: ChatSession | null;
  onSelectSession: (session: ChatSession) => void;
  onDeleteSession: (sessionId: string) => void;
  onArchiveSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, title: string) => void;
  onRestoreSession?: (sessionId: string) => void;
  onPinSession?: (sessionId: string) => void;
  pinnedSessions?: Set<string>;
}

export function SessionList({
  sessions,
  activeSession,
  onSelectSession,
  onDeleteSession,
  onArchiveSession,
  onRenameSession,
  onRestoreSession,
  onPinSession,
  pinnedSessions = new Set(),
}: SessionListProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [expandedMenuId, setExpandedMenuId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterMode, setFilterMode] = useState<'active' | 'archived' | 'all'>('active');
  const [showArchived, setShowArchived] = useState(false);
  const [showMoreActive, setShowMoreActive] = useState(false);
  const [showMoreArchived, setShowMoreArchived] = useState(false);

  const INITIAL_DISPLAY_COUNT = 5;

  // Separate active and archived sessions
  const activeSessions = useMemo(
    () => sessions.filter((s) => s.status === 'active'),
    [sessions]
  );

  const archivedSessions = useMemo(
    () => sessions.filter((s) => s.status === 'archived'),
    [sessions]
  );

  // Filter and search logic
  const filteredActiveSessions = useMemo(() => {
    if (filterMode === 'archived') return [];
    return activeSessions.filter((session) =>
      session.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      session.preview.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [activeSessions, searchQuery, filterMode]);

  const filteredArchivedSessions = useMemo(() => {
    if (filterMode === 'active') return [];
    return archivedSessions.filter((session) =>
      session.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      session.preview.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [archivedSessions, searchQuery, filterMode]);

  // Separate pinned and unpinned
  const pinnedActiveSessions = useMemo(
    () => filteredActiveSessions.filter((s) => pinnedSessions.has(s.id)),
    [filteredActiveSessions, pinnedSessions]
  );

  const unpinnedActiveSessions = useMemo(
    () => filteredActiveSessions.filter((s) => !pinnedSessions.has(s.id)),
    [filteredActiveSessions, pinnedSessions]
  );

  // Pagination
  const displayedActivePinned = pinnedActiveSessions.slice(0, INITIAL_DISPLAY_COUNT);
  const displayedActiveUnpinned = unpinnedActiveSessions.slice(
    0,
    showMoreActive ? unpinnedActiveSessions.length : INITIAL_DISPLAY_COUNT
  );

  const displayedArchived = archivedSessions.slice(
    0,
    showMoreArchived ? archivedSessions.length : INITIAL_DISPLAY_COUNT
  );

  const handleStartEdit = (session: ChatSession) => {
    setEditingId(session.id);
    setEditingTitle(session.title);
    setExpandedMenuId(null);
  };

  const handleSaveEdit = (sessionId: string) => {
    if (editingTitle.trim()) {
      onRenameSession(sessionId, editingTitle);
    }
    setEditingId(null);
    setEditingTitle('');
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditingTitle('');
  };

  const handleKeyDown = (e: React.KeyboardEvent, sessionId: string) => {
    if (e.key === 'Enter') {
      handleSaveEdit(sessionId);
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  const formatRelativeTime = (timestamp: number): string => {
    const now = Date.now();
    const diffMs = now - timestamp * 1000;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return new Date(timestamp * 1000).toLocaleDateString();
  };

  const SessionItemContent = ({ session }: { session: ChatSession }) => (
    <>
      {editingId === session.id ? (
        <div className="px-3 py-2">
          <input
            type="text"
            value={editingTitle}
            onChange={(e) => setEditingTitle(e.target.value)}
            onKeyDown={(e) => handleKeyDown(e, session.id)}
            onBlur={() => handleSaveEdit(session.id)}
            autoFocus
            className="w-full rounded px-2 py-1 text-sm font-medium bg-white border border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Edit session title"
          />
        </div>
      ) : (
        <button
          onClick={() => onSelectSession(session)}
          className="w-full text-left px-3 py-2 flex-1"
          aria-current={activeSession?.id === session.id ? 'page' : undefined}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              {/* Title */}
              <p className="font-medium text-sm text-slate-900 truncate">
                {session.title}
              </p>

              {/* Preview */}
              {session.preview && (
                <p className="text-xs text-slate-600 truncate mt-1">
                  {session.preview}
                </p>
              )}

              {/* Timestamp */}
              <p className="text-xs text-slate-500 mt-1">
                {formatRelativeTime(session.last_message_at)}
              </p>
            </div>
          </div>
        </button>
      )}

      {/* Session Actions Menu */}
      {activeSession?.id === session.id && (
        <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="relative">
            <button
              onClick={() => setExpandedMenuId(expandedMenuId === session.id ? null : session.id)}
              className="p-1 hover:bg-blue-200 rounded text-slate-600 hover:text-slate-900"
              aria-label="Session menu"
              aria-expanded={expandedMenuId === session.id}
              aria-haspopup="menu"
            >
              <MoreVertical size={16} />
            </button>

            {/* Dropdown Menu */}
            {expandedMenuId === session.id && (
              <div
                className="absolute right-0 mt-1 w-48 bg-white rounded-lg shadow-lg border border-slate-200 z-10"
                role="menu"
              >
                {/* Pin/Unpin */}
                {onPinSession && (
                  <>
                    <button
                      onClick={() => {
                        onPinSession(session.id);
                        setExpandedMenuId(null);
                      }}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-slate-100 flex items-center gap-2 text-slate-700"
                      role="menuitem"
                    >
                      <Star size={14} className={pinnedSessions.has(session.id) ? 'fill-yellow-400 text-yellow-400' : ''} />
                      {pinnedSessions.has(session.id) ? 'Unpin' : 'Pin to top'}
                    </button>
                  </>
                )}

                {/* Rename */}
                <button
                  onClick={() => {
                    handleStartEdit(session);
                    setExpandedMenuId(null);
                  }}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-slate-100 flex items-center gap-2 text-slate-700"
                  role="menuitem"
                >
                  <Edit2 size={14} />
                  Rename
                </button>

                {/* Archive/Restore */}
                {session.status === 'active' ? (
                  <button
                    onClick={() => {
                      onArchiveSession(session.id);
                      setExpandedMenuId(null);
                    }}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-slate-100 flex items-center gap-2 text-slate-700"
                    role="menuitem"
                  >
                    <Archive size={14} />
                    Archive
                  </button>
                ) : onRestoreSession ? (
                  <button
                    onClick={() => {
                      onRestoreSession(session.id);
                      setExpandedMenuId(null);
                    }}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-slate-100 flex items-center gap-2 text-slate-700"
                    role="menuitem"
                  >
                    <RotateCcw size={14} />
                    Restore
                  </button>
                ) : null}

                <div className="border-t border-slate-200" />

                {/* Delete */}
                <button
                  onClick={() => {
                    onDeleteSession(session.id);
                    setExpandedMenuId(null);
                  }}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-red-50 flex items-center gap-2 text-red-600"
                  role="menuitem"
                >
                  <Trash2 size={14} />
                  Delete
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Search and Filter Bar */}
      <div className="flex-shrink-0 px-3 py-3 border-b border-white/10 space-y-3">
        {/* Search Input */}
        <div className="relative">
          <Search size={16} className="absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search sessions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-lg text-sm bg-white/50 border border-white/20 text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:bg-white transition-colors"
            aria-label="Search sessions"
          />
        </div>

        {/* Filter Buttons */}
        <div className="flex gap-2">
          {['active', 'archived', 'all'].map((mode) => (
            <button
              key={mode}
              onClick={() => setFilterMode(mode as 'active' | 'archived' | 'all')}
              className={`px-3 py-1 text-xs rounded-full font-medium transition-colors ${
                filterMode === mode
                  ? 'bg-blue-500 text-white'
                  : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
              }`}
            >
              {mode.charAt(0).toUpperCase() + mode.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto pr-2">
        {filteredActiveSessions.length === 0 && filteredArchivedSessions.length === 0 ? (
          <div className="flex h-full items-center justify-center px-4 py-8">
            <div className="text-center">
              <p className="text-sm text-slate-500 mb-2">
                {searchQuery ? 'No matching conversations' : 'No conversations yet'}
              </p>
              <p className="text-xs text-slate-400">
                {searchQuery ? 'Try adjusting your search' : 'Create a new chat to get started'}
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-2 p-2">
            {/* Pinned Sessions Section */}
            {displayedActivePinned.length > 0 && (
              <div>
                <div className="px-2 py-1">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Pinned</p>
                </div>
                <div className="space-y-1">
                  {displayedActivePinned.map((session) => (
                    <div
                      key={session.id}
                      className={`group relative rounded-lg transition-all duration-200 cursor-pointer ${
                        activeSession?.id === session.id
                          ? 'bg-blue-100 border border-blue-300 shadow-md'
                          : 'border border-transparent hover:bg-slate-100'
                      }`}
                    >
                      <SessionItemContent session={session} />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Active Sessions Section */}
            {displayedActiveUnpinned.length > 0 && (
              <div>
                {displayedActivePinned.length > 0 && (
                  <div className="px-2 py-1 mt-2">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active</p>
                  </div>
                )}
                <div className="space-y-1">
                  {displayedActiveUnpinned.map((session) => (
                    <div
                      key={session.id}
                      className={`group relative rounded-lg transition-all duration-200 cursor-pointer ${
                        activeSession?.id === session.id
                          ? 'bg-blue-100 border border-blue-300 shadow-md'
                          : 'border border-transparent hover:bg-slate-100'
                      }`}
                    >
                      <SessionItemContent session={session} />
                    </div>
                  ))}
                </div>

                {/* Load More Active */}
                {unpinnedActiveSessions.length > INITIAL_DISPLAY_COUNT && (
                  <button
                    onClick={() => setShowMoreActive(!showMoreActive)}
                    className="mt-2 w-full px-3 py-2 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors flex items-center justify-center gap-2"
                  >
                    <ChevronDown
                      size={14}
                      className={`transition-transform ${showMoreActive ? 'rotate-180' : ''}`}
                    />
                    {showMoreActive ? 'Show less' : `Load more (${unpinnedActiveSessions.length - INITIAL_DISPLAY_COUNT})`}
                  </button>
                )}
              </div>
            )}

            {/* Archived Sessions Section */}
            {filteredArchivedSessions.length > 0 && (
              <div className="mt-4">
                <button
                  onClick={() => setShowArchived(!showArchived)}
                  className="w-full px-2 py-2 flex items-center gap-2 text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  <ChevronDown
                    size={14}
                    className={`transition-transform ${showArchived ? 'rotate-180' : ''}`}
                  />
                  Archived ({filteredArchivedSessions.length})
                </button>

                {showArchived && (
                  <div className="mt-2 space-y-1">
                    {displayedArchived.map((session) => (
                      <div
                        key={session.id}
                        className={`group relative rounded-lg transition-all duration-200 cursor-pointer opacity-75 ${
                          activeSession?.id === session.id
                            ? 'bg-blue-100 border border-blue-300 shadow-md'
                            : 'border border-transparent hover:bg-slate-100'
                        }`}
                      >
                        <SessionItemContent session={session} />
                      </div>
                    ))}

                    {/* Load More Archived */}
                    {archivedSessions.length > INITIAL_DISPLAY_COUNT && (
                      <button
                        onClick={() => setShowMoreArchived(!showMoreArchived)}
                        className="mt-2 w-full px-3 py-2 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors flex items-center justify-center gap-2"
                      >
                        <ChevronDown
                          size={14}
                          className={`transition-transform ${showMoreArchived ? 'rotate-180' : ''}`}
                        />
                        {showMoreArchived ? 'Show less' : `Load more (${archivedSessions.length - INITIAL_DISPLAY_COUNT})`}
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
