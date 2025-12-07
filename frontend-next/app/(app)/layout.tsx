import { AppShell } from '@/components/layout';
import { AuthGuard } from '@/lib/middleware/auth-guard';

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <AppShell>{children}</AppShell>
    </AuthGuard>
  );
}







