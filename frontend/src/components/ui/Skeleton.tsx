import { cn } from '@/lib/utils';

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('animate-pulse rounded-md bg-slate-200', className)}
      aria-hidden="true"
      {...props}
    />
  );
}

export function ArticleCardSkeleton() {
  return (
    <div className="article-glass-card h-full p-5 sm:p-6">
      <div className="mr-4">
        <Skeleton className="h-12 w-12 rounded-2xl bg-white/70" />
      </div>
      <div className="flex flex-1 flex-col">
        <Skeleton className="mb-4 h-7 w-24 rounded-full bg-white/70" />
        <Skeleton className="mb-3 h-8 w-4/5 rounded-2xl bg-white/75" />
        <Skeleton className="mb-3 h-4 w-full rounded-full bg-white/60" />
        <Skeleton className="mb-6 h-4 w-3/4 rounded-full bg-white/60" />
        <div className="mt-auto flex items-center justify-between border-t border-black/5 pt-4">
          <Skeleton className="h-5 w-28 rounded-full bg-white/65" />
          <Skeleton className="h-9 w-24 rounded-2xl bg-white/65" />
        </div>
      </div>
    </div>
  );
}

export function SearchResultSkeleton() {
  return (
    <div className="border-b border-slate-200 pb-6">
      <div className="flex gap-4">
        <Skeleton className="h-32 w-48 rounded-lg" />
        <div className="flex-1">
          <Skeleton className="mb-2 h-6 w-3/4" />
          <Skeleton className="mb-2 h-4 w-full" />
          <Skeleton className="mb-4 h-4 w-full" />
          <div className="flex gap-2">
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
        </div>
      </div>
    </div>
  );
}
