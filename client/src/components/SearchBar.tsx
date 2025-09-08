import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';


type SearchBarProps = {
    initialValue?: string;
};

const SearchBar: React.FC<SearchBarProps> = ({ initialValue }) => {
    const [searchTerm, setSearchTerm] = useState(initialValue || '');
    const navigate = useNavigate();


    const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        setSearchTerm(event.target.value);
    };

    const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
        if (event.key === 'Enter') {
            handleSubmit();
        }
    };

    const handleSubmit = async () => {
        navigate(`/search?query=${searchTerm}`);
    };

    return (
        <motion.div
            whileHover={{ scale: 1.02 }}
            whileFocus={{ scale: 1.02 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            className="w-3/5 my-4 mx-auto" // Make the container full width
        >
            <div className="relative flex items-center">
                <input
                    type="text"
                    id="search-input"
                    value={searchTerm}
                    onChange={handleChange}
                    onKeyDown={handleKeyDown}
                    placeholder="Search"
                    className="h-16 pl-10 pr-16 py-2 rounded-full w-full bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-md"
                />
                <button
                    onClick={handleSubmit}
                    className="absolute right-4 p-2 rounded-full hover:bg-gray-100 focus:outline-none"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6">
                        <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
                    </svg>

                </button>
            </div>
        </motion.div>
    );
};

export default SearchBar;