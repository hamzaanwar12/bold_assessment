import { LazyMotion, MotionConfig } from "motion/react";
import { AppShell } from "./components/AppShell";
import { CandidateView } from "./CandidateView";

const loadMotionFeatures = () => import("./motionFeatures").then((m) => m.default);

function App() {
  return (
    // `strict` makes any full `motion.*` import an error, keeping the engine
    // lazy; reducedMotion="user" honours the OS setting.
    <LazyMotion features={loadMotionFeatures} strict>
      <MotionConfig reducedMotion="user">
        <AppShell>
          <CandidateView />
        </AppShell>
      </MotionConfig>
    </LazyMotion>
  );
}

export default App;
