import { IconRadar } from './icons';

export default function Footer() {
  return (
    <footer className="border-t border-white/[0.05] py-8">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6">
        <div className="flex items-center gap-2.5">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-violet-600 text-white">
            <IconRadar />
          </div>
          <span className="text-xs font-semibold text-slate-500">LidScout</span>
        </div>
        <p className="text-xs text-slate-700">Evidence-backed market intelligence</p>
      </div>
    </footer>
  );
}
