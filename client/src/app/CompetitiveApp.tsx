import React from 'react';
import DailyNewsletter from '../pages/DailyNewsletter';



interface CompetitiveAppProps { }

const CompetitiveApp: React.FC<CompetitiveAppProps> = () => {

    return (
        <div className="flex">
            <div className="flex flex-col h-full w-full overflow-y-auto bg-gray-100 dark:bg-black">

                <DailyNewsletter />
            </div>
        </div>
    );



}

export default CompetitiveApp