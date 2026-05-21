import { ArticleCardSkeleton, Skeleton } from '@/components/ui/Skeleton';
import { Bookmark, CheckSquare, FileText, Search, User } from 'lucide-react';

type LoadingVariant = 'default' | 'articles' | 'search' | 'profile' | 'queue' | 'article';

interface AppLoadingStateProps {
  variant?: LoadingVariant;
}

const variantCopy: Record<LoadingVariant, { label: string; title: string; subtitle: string; icon: typeof FileText }> = {
  default: {
    label: 'Loading',
    title: 'Preparing your workspace',
    subtitle: 'The interface is ready while fresh data loads in.',
    icon: FileText,
  },
  articles: {
    label: 'Articles',
    title: 'Loading articles',
    subtitle: 'Filters and article cards will fill in as soon as the API returns.',
    icon: FileText,
  },
  search: {
    label: 'Browse',
    title: 'Search the tech signal',
    subtitle: 'Enter a topic while the search tools warm up.',
    icon: Search,
  },
  profile: {
    label: 'Profile',
    title: 'Loading profile',
    subtitle: 'Account details, preferences, and saved articles are on the way.',
    icon: User,
  },
  queue: {
    label: 'Admin',
    title: 'Loading queue',
    subtitle: 'Pending search results will appear in the review table shortly.',
    icon: CheckSquare,
  },
  article: {
    label: 'Article',
    title: 'Loading article',
    subtitle: 'The story preview and reading details are being prepared.',
    icon: Bookmark,
  },
};

function HeroSkeleton({ variant }: { variant: LoadingVariant }) {
  const copy = variantCopy[variant];
  const Icon = copy.icon;

  return (
    <section className="app-hero-panel mb-8 p-5 sm:p-7">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white/75 shadow-[inset_0_1px_0_rgba(255,255,255,0.85),0_12px_28px_rgba(0,122,255,0.18)]">
            <Icon className="h-5 w-5 text-[#007AFF]" />
          </div>
          <div>
            <p className="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-black/45">{copy.label}</p>
            <h1 className="font-sans text-3xl font-bold text-black sm:text-4xl">{copy.title}</h1>
            <p className="mt-2 max-w-2xl text-sm text-black/60 sm:text-base">{copy.subtitle}</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <Skeleton className="h-11 w-32 rounded-2xl bg-white/65" />
          <Skeleton className="h-11 w-28 rounded-2xl bg-white/45" />
        </div>
      </div>
    </section>
  );
}

function ArticleGridSkeleton() {
  return (
    <>
      <div className="compact-toolbar mb-6">
        {[0, 1, 2, 3].map((item) => (
          <Skeleton key={item} className="h-9 w-28 rounded-full bg-white/65" />
        ))}
      </div>
      <div className="glass-grid">
        {[0, 1, 2, 3, 4, 5].map((item) => (
          <ArticleCardSkeleton key={item} />
        ))}
      </div>
    </>
  );
}

function QueueTableSkeleton() {
  return (
    <div className="queue-review-list">
      {[0, 1, 2, 3].map((item) => (
        <div key={item} className="queue-review-row">
          <div>
            <Skeleton className="mb-3 h-6 w-4/5 rounded-xl bg-white/70" />
            <Skeleton className="mb-3 h-4 w-full rounded-xl bg-white/55" />
            <Skeleton className="h-4 w-2/3 rounded-xl bg-white/55" />
          </div>
          <div className="queue-review-meta">
            <Skeleton className="h-7 w-24 rounded-full bg-white/65" />
            <Skeleton className="h-7 w-24 rounded-full bg-white/65" />
          </div>
          <div className="queue-review-actions">
            <Skeleton className="h-10 w-28 rounded-2xl bg-white/70" />
            <Skeleton className="h-10 w-24 rounded-2xl bg-white/55" />
            <Skeleton className="h-10 w-10 rounded-2xl bg-white/55" />
          </div>
        </div>
      ))}
    </div>
  );
}

function ProfileSkeleton() {
  return (
    <div className="glass-panel p-6 sm:p-8">
      <Skeleton className="mb-7 h-8 w-56 rounded-xl bg-white/70" />
      <div className="grid gap-6 md:grid-cols-2">
        {[0, 1, 2].map((item) => (
          <div key={item}>
            <Skeleton className="mb-3 h-4 w-28 rounded-full bg-white/60" />
            <Skeleton className="h-14 rounded-2xl bg-white/75" />
          </div>
        ))}
      </div>
    </div>
  );
}

function SearchSkeleton() {
  return (
    <div className="browse-search-stage">
      <div className="browse-entry-panel">
        <div className="mx-auto mb-6 max-w-2xl text-center">
          <Skeleton className="mx-auto mb-4 h-12 w-3/4 rounded-2xl bg-white/55" />
          <Skeleton className="mx-auto h-5 w-2/3 rounded-full bg-white/45" />
        </div>
        <Skeleton className="h-16 rounded-[28px] bg-white/75" />
        <div className="browse-suggestion-row mt-6">
          {[0, 1, 2, 3, 4].map((item) => (
            <Skeleton key={item} className="h-10 w-28 rounded-full bg-white/65" />
          ))}
        </div>
      </div>
    </div>
  );
}

export function AppLoadingState({ variant = 'default' }: AppLoadingStateProps) {
  return (
    <main className="app-page-shell search-stage" id="main-content" aria-busy="true">
      <div className="app-page-container">
        {variant !== 'search' && <HeroSkeleton variant={variant} />}
        {variant === 'search' ? <SearchSkeleton /> : null}
        {variant === 'articles' || variant === 'default' ? <ArticleGridSkeleton /> : null}
        {variant === 'queue' ? <QueueTableSkeleton /> : null}
        {variant === 'profile' ? <ProfileSkeleton /> : null}
        {variant === 'article' ? (
          <div className="glass-panel p-6 sm:p-8">
            <Skeleton className="mb-5 h-12 w-4/5 rounded-2xl bg-white/70" />
            <Skeleton className="mb-3 h-5 w-full rounded-full bg-white/55" />
            <Skeleton className="mb-8 h-5 w-2/3 rounded-full bg-white/55" />
            <div className="grid gap-4 sm:grid-cols-2">
              <Skeleton className="h-24 rounded-3xl bg-white/70" />
              <Skeleton className="h-24 rounded-3xl bg-white/70" />
            </div>
          </div>
        ) : null}
      </div>
    </main>
  );
}
