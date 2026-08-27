import { instrument } from "@/lib/instrument";
import { QuizApp } from "@/components/QuizApp";

export const metadata = { title: "Learner Score — the questions" };

export default function QuizPage() {
  // Only the instrument itself crosses to the client — scoring stays on the
  // server (§5).
  return <QuizApp instrument={instrument} />;
}
