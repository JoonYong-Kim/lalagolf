import Link from "next/link";

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/rounds", label: "Rounds" },
  { href: "/analysis", label: "Analysis" },
  { href: "/ask", label: "Ask" },
  { href: "/upload", label: "Upload" },
  { href: "/admin/uploads/errors", label: "Admin" },
];

export function AppShell({
  children,
  eyebrow,
  title,
}: {
  children: React.ReactNode;
  eyebrow: string;
  title: string;
}) {
  return (
    <main className="min-h-screen bg-surface text-ink">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl gap-6 px-4 py-4 pb-20 md:px-6 md:pb-6">
        <aside className="hidden w-52 shrink-0 border-r border-line pr-4 md:block">
          <div className="sticky top-4">
            <Link className="block text-lg font-semibold" href="/dashboard">
              LalaGolf
            </Link>
            <nav className="mt-8 space-y-1">
              {navItems.map((item) => (
                <Link
                  className="block rounded-md px-3 py-2 text-sm font-medium text-muted hover:bg-white hover:text-ink"
                  href={item.href}
                  key={item.href}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </aside>

        <section className="min-w-0 flex-1">
          <header className="border-b border-line pb-4">
            <p className="text-sm font-medium text-green-700">{eyebrow}</p>
            <h1 className="mt-2 text-2xl font-semibold md:text-3xl">{title}</h1>
          </header>
          {children}
        </section>
      </div>

      <nav className="fixed inset-x-0 bottom-0 grid grid-cols-5 border-t border-line bg-white md:hidden">
        {navItems.slice(0, 5).map((item) => (
          <Link className="px-2 py-3 text-center text-sm font-semibold" href={item.href} key={item.href}>
            {item.label}
          </Link>
        ))}
      </nav>
    </main>
  );
}
