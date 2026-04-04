import { useEffect } from "react";
import { useStore } from "../store";

export function useKeyboard() {
  const triageFinding = useStore((s) => s.triageFinding);
  const navigateFinding = useStore((s) => s.navigateFinding);
  const selectedFinding = useStore((s) => s.selectedFinding);

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      // Ignore when typing in inputs
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      if (!selectedFinding) return;

      switch (e.key) {
        case "c":
          triageFinding(
            selectedFinding.id,
            selectedFinding.triage_status === "confirmed"
              ? "pending"
              : "confirmed",
          );
          break;
        case "d":
          triageFinding(
            selectedFinding.id,
            selectedFinding.triage_status === "dismissed"
              ? "pending"
              : "dismissed",
          );
          break;
        case "n":
          navigateFinding("next");
          break;
        case "p":
          navigateFinding("prev");
          break;
      }
    }

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selectedFinding, triageFinding, navigateFinding]);
}
