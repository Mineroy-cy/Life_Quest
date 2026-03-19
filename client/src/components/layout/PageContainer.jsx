import Navbar from "./Navbar";
import Sidebar from "./Sidebar";

export default function PageContainer({ title, subtitle, children }) {
  return (
    <div className="min-h-screen bg-app-pattern text-slate-800">
      <Navbar />
      <main className="mx-auto grid max-w-7xl gap-6 px-4 py-6 md:grid-cols-[1fr_280px]">
        <section className="space-y-4">
          <header className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h1 className="font-display text-2xl font-semibold text-slate-900">{title}</h1>
            {subtitle ? <p className="mt-1 text-sm text-slate-600">{subtitle}</p> : null}
          </header>
          {children}
        </section>
        <Sidebar />
      </main>
    </div>
  );
}
