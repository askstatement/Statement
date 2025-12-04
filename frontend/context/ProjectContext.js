// context/AppContext.js
import React, { createContext, useContext, useState } from "react";

const ProjectContext = createContext();

export const ProjectProvider = ({ children }) => {
  const [project, setProject] = useState({});

  const updateProjectContext = (updates) => {
    setProject((prev) => ({ ...prev, ...updates }));
  };

  return (
    <ProjectContext.Provider value={{ project, updateProjectContext }}>
      {children}
    </ProjectContext.Provider>
  );
};

export const useProjectContext = () => {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error("useProjectContext must be used within an ProjectContext");
  }
  return context;
};
