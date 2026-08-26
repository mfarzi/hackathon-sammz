import type { SiteReply } from "@/lib/consultScript";
import { WireBox } from "./WireBox";

export function SiteReplyMessage({ reply }: { reply: SiteReply }) {
  return (
    <>
      <p>
        <strong className="font-semibold">{reply.headline}</strong>
      </p>
      {reply.paragraphs.map((p, i) => (
        <p key={i}>{p}</p>
      ))}
      <WireBox sent={reply.sent} held={reply.held} />
    </>
  );
}
