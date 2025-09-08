import React, { createContext, useState } from 'react';

export interface NewsletterContextType {
    nlId: string | null,
    setNlId: (id: string | null) => void,
    isNewDailyNL: boolean,
    setIsNewDailyNL: (val: boolean) => void,
    digestId: string | null,
    setDigestId: (id: string | null) => void,
    isNewDigest: boolean,
    setIsNewDigest: (val: boolean) => void,
}

export const NewsletterContext = createContext<NewsletterContextType | null>(null)

export const NewsletterProvider = ({ children }: { children: React.ReactNode }) => {
    const [nlId, setNlId] = useState<string | null>(null);
    const [digestId, setDigestId] = useState<string | null>(null);
    const [isNewDailyNL, setIsNewDailyNL] = useState(true);
    const [isNewDigest, setIsNewDigest] = useState(true);


    return (
        <NewsletterContext.Provider value={{
            nlId,
            setNlId,
            isNewDailyNL,
            setIsNewDailyNL,
            digestId,
            setDigestId,
            isNewDigest,
            setIsNewDigest
        }}>
            {children}
        </NewsletterContext.Provider>
    );
};