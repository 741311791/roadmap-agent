import { AuthGuard } from '@/lib/middleware/auth-guard';

export default function ImmersiveLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      {children}
    </AuthGuard>
  );
}

