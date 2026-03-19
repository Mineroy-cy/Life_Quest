import { createContext, useContext, useMemo } from "react";
import { useProjects } from "../hooks/useProjects";

const ProjectContext = createContext(null);

export function ProjectProvider({ children }) {
  const projectState = useProjects();
  const value = useMemo(() => projectState, [projectState]);

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

export function useProjectContext() {
  const ctx = useContext(ProjectContext);
  if (!ctx) {
    throw new Error("useProjectContext must be used inside ProjectProvider");
  }
  return ctx;
}
