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
    <div className="h-full rounded-lg border border-slate-200 bg-white p-6">
      <Skeleton className="mb-3 h-6 w-24 rounded-full" />
      <Skeleton className="mb-3 h-6 w-full" />
      <Skeleton className="mb-3 h-4 w-full" />
      <Skeleton className="mb-4 h-4 w-3/4" />
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-16" />
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
