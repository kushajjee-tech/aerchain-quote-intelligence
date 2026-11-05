import { createContext, useContext } from "react";
export const RfxContext = createContext<{ rfxId: number; setRfxId: (n: number) => void }>({ rfxId: 1, setRfxId: () => {} });
export const useRfx = () => useContext(RfxContext);
