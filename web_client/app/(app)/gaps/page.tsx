import { redirect } from 'next/navigation';

export default function LegacyGapsRedirect() {
  redirect('/markets');
}
