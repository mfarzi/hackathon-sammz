import { FOLLOW_UP } from "@/lib/consultScript";
import { WireBox } from "./WireBox";

export function FollowUpAnswers() {
  return (
    <>
      {FOLLOW_UP.answers.map((a) => (
        <p key={a.site}>
          <strong className="font-semibold">{a.site}:</strong> {a.answer}
        </p>
      ))}
      <WireBox sent={FOLLOW_UP.sent} held={FOLLOW_UP.held} />
    </>
  );
}
