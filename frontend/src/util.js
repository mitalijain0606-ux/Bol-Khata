// Small shared helpers.
export const fmt = (n) =>
  "₹" + Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 });

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// "2026-11-16" / "2026-11-16 10:00:00" -> "aaj" | "kal" | "16 Nov"
export function fmtDate(iso, { relative = true } = {}) {
  if (!iso) return "—";
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  if (!y || !m || !d) return iso;
  if (relative) {
    const today = new Date();
    const t0 = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const diff = Math.round((new Date(y, m - 1, d) - t0) / 86400000);
    if (diff === 0) return "aaj";
    if (diff === 1) return "kal";
    if (diff === -1) return "kal (beeta)";
  }
  return `${d} ${MONTHS[m - 1]}`;
}

// WhatsApp reminder. No phone number is put in the link on purpose: WhatsApp
// opens its contact picker, so a wrong or made-up number can never be messaged.
export function whatsappLink({ name, shop, balance, promise }) {
  const lines = [
    `Namaste ${name} ji 🙏`,
    `${shop || "Dukaan"} ki taraf se yaad dila rahe hain — aapka ${fmt(balance)} udhaar baki hai.`,
  ];
  if (promise) {
    lines.push(`Aapne ${fmt(promise.amount)} ${fmtDate(promise.due_date, { relative: false })} tak dene ka wada kiya hai.`);
  }
  lines.push("Samay par bhugtan ke liye dhanyavaad!");
  return "https://wa.me/?text=" + encodeURIComponent(lines.join("\n"));
}
