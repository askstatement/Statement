import { createContext, useContext } from 'react';

export const SessionContext = createContext(null);

export const useSession = () => useContext(SessionContext);
