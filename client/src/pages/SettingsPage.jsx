import PageContainer from "../components/layout/PageContainer";

export default function SettingsPage() {
  return (
    <PageContainer title="Settings" subtitle="Preparation area for future auth, reminders, and notification preferences.">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="font-display text-lg font-semibold text-slate-900">System Readiness</h2>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600">
          <li>Axios instance is token-ready for future authentication.</li>
          <li>Challenge state persists in local storage across refreshes.</li>
          <li>Global toast notifications capture API/network failures.</li>
        </ul>
      </section>
    </PageContainer>
  );
}
