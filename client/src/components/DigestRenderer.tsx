import React, { useContext } from 'react';
import { Digest } from '../dto/InterfaceDefinition'; // Adjust path if needed
import { NewsItem } from './NewsList2';
import { Save } from 'lucide-react';
import ApiHelper from '../backend/ApiHelper';
import { NewsletterContext, NewsletterContextType } from '../context/NewsletterContext';
import { ButtonConfig } from './NewsList2';
import { marked } from 'marked';
import * as Collapsible from "@radix-ui/react-collapsible";
import { RowSpacingIcon, Cross2Icon } from "@radix-ui/react-icons";
import { ArrowPathIcon } from '@heroicons/react/24/outline';


interface DigestRendererProps {
    digestData: Digest | null;
    setDigestData: React.Dispatch<React.SetStateAction<Digest | null>>;
    contentbuttons: ButtonConfig[];
    highlightButtons: ButtonConfig[]

}


interface DigestSectionHeader {
    title: string;
    icon: React.ReactNode;
}
const DigestSectionHeader: React.FC<DigestSectionHeader> = ({ title, icon }) => {
    return (
        <div className="bg-slate-200 shadow-md rounded-lg mb-4 ml-2">
            <div className="items-center p-4 flex space-x-3">
                {icon}
                <h2 className="text-md font-bold text-gray-800">{title}</h2>
            </div>
        </div>
    )
}

const DigestSubSection: React.FC<DigestSectionHeader> = ({ title }) => {
    return (
        <div className="bg-slate-100 shadow-md rounded-lg mb-4 ml-6">
            <div className="items-center p-4 flex space-x-3">
                <h2 className="text-md font-bold text-gray-800">{title}</h2>
            </div>
        </div>
    )
}


const WorldIcon = () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418" />
</svg>




const DigestRenderer: React.FC<DigestRendererProps> = ({ digestData, setDigestData, contentbuttons, highlightButtons }) => {
    const { digestId, setDigestId, setIsNewDigest } = useContext(NewsletterContext) as NewsletterContextType
    const [higlightNewsOpen, setHighlightNewsOpen] = React.useState(false);
    const [highlightRefreshing, setHighlightRefreshing] = React.useState(false);



    const handleSave = async () => {
        // Call the Save API
        if (!digestData) return;
        if (!digestId) {
            const digestId = await ApiHelper.saveDigest(digestData);
            setDigestId(digestId);
            setIsNewDigest(false);

        } else {
            await ApiHelper.saveDigest(digestData, digestId);
        }
    }

    const handleDelete = async () => {
        if (digestId) {
            await ApiHelper.deleteDigest(digestId);
            setDigestId(null);
            setIsNewDigest(true);
        }
    }

    const handleGenerateHighlights = async () => {
        if (!digestData) return;
        try {
            setHighlightRefreshing(true);
            //Updating the digest
            const highlight = await ApiHelper.generateDigestHighlight(digestData);
            setDigestData({ ...digestData, highlight: highlight });

            setHighlightRefreshing(false);
        } catch {
            setHighlightRefreshing(false);
            console.log("Error generating highlight")
        }

    }



    const renderSummary = () => {
        if (digestData?.highlight.markdown_text) {
            const html = marked.parse(digestData.highlight.markdown_text);
            return (
                <div className="prose prose-lg  max-w-3xl"> {/* Added prose classes */}
                    <div dangerouslySetInnerHTML={{ __html: html }} />
                </div>
            );
        } else {
            return <p className="text-gray-500">No summary available.</p>;
        }
    };



    return (
        <div className="p-4  rounded-lg">
            <div className="bg-white shadow-md rounded-lg mb-4 flex">
                <div className="items-center p-4 flex space-x-3">
                    <img src='/spark.png' alt='logo' className='w-8 h-8' />
                    <h3 className="text-lg font-bold text-gray-600">Generated Digest</h3>
                </div>
                <div className='flex  justify-between ml-auto space-x-4 mr-8 items-center'>

                    <button onClick={handleSave} className=" inline-flex items-center w-24 h-8 px-4  text-sm bg-blue-500 transition-colors duration-150 rounded-lg focus:shadow-outline hover:bg-blue-700 text-white font-bold 
                     focus:outline-none">
                        <Save className='mr-2' size={20} />
                        Save
                    </button>
                    <button onClick={handleDelete} className="bg-red-400 hover:bg-red-500 h-8 px-4  transition-colors duration-150 rounded-lg focus:shadow-outline text-sm text-white font-bold focus:outline-none">
                        Delete
                    </button>
                </div>
            </div >
            {digestData && (
                <div className='overflow-y-auto max-h-[700px]'>
                    {/* Highlight Section */}
                    <div className="p-4 bg-white rounded-lg mb-4">
                        <h2 className="text-lg font-bold mb-2">
                            <div className="inline-flex items-center">
                                Highlights
                                <button onClick={handleGenerateHighlights} disabled={highlightRefreshing} className={`disabled:text-blue-300 text-blue-500 ml-2 ${highlightRefreshing ? 'animate-spin' : ''}`}>
                                    <ArrowPathIcon className="h-5 w-5" />
                                </button>

                            </div>

                        </h2>
                        {renderSummary()}
                        <div className="mt-2">
                            <Collapsible.Root open={higlightNewsOpen} onOpenChange={setHighlightNewsOpen}>
                                <div className="flex items-center justify-between">
                                    <span className=" text-[15px] leading-[25px] text-white">

                                    </span>

                                </div>
                                <div className="flex flex-col my-2.5 mx-4 rounded bg-white p-2.5 shadow-[0_1px_5px] shadow-gray-300">
                                    <div className="flex" >

                                        <Collapsible.Trigger asChild>
                                            <button className="inline-flex size-[25px] items-center justify-center rounded-full shadow-[0_2px_10px] shadow-customer-blue outline-none hover:bg-customer-blue  data-[state=closed]:bg-white data-[state=open]:bg-blue-500 data-[state=open]:text-white">
                                                {higlightNewsOpen ? <Cross2Icon /> : <RowSpacingIcon />}
                                            </button>
                                        </Collapsible.Trigger>
                                        <span className="text-[15px] leading-[25px] ml-2">
                                            Highlight News
                                        </span>
                                    </div>


                                    <Collapsible.Content>
                                        {digestData.highlight.news.map((item, index) => (
                                            <NewsItem key={index} news={item} buttons={highlightButtons} />
                                        ))}
                                    </Collapsible.Content>
                                </div>



                            </Collapsible.Root>

                        </div>
                    </div>

                    {/* Sections */}
                    {digestData.sections.map((section, index) => (
                        <div key={index} className="p-4 bg-white rounded-lg mb-4">
                            <DigestSectionHeader title={section.name} icon={<WorldIcon />} />
                            {section.news && (
                                <div>
                                    {section.news.map((item, index) => (
                                        <NewsItem key={index} news={item} buttons={contentbuttons} />
                                    ))}
                                </div>
                            )}
                            {section.subSections && section.subSections.map((subSection, index) => (
                                <div key={index} className="mt-4">
                                    <DigestSubSection title={subSection.name} icon={<WorldIcon />} />
                                    <div className="ml-6" >
                                        {subSection.news.map((item, index) => (
                                            <NewsItem key={index} news={item} buttons={contentbuttons} />
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default DigestRenderer;