import React from 'react';
import { motion } from 'framer-motion';

const MenuLoadingSkeleton: React.FC = () => {
    return (
        <div className="px-4 absolute right-0 mt-2 rounded-md shadow-md py-2 w-60 animate-pulse"> {/* Added animate-pulse */}


            {/* Recent items section placeholder */}
            <div className="mb-2">

                {[...Array(5)].map((_, index) => (
                    <motion.div
                        key={index}
                        className="flex items-center justify-between p-2 rounded-md bg-gray-100 my-2 animate-pulse"
                        whileHover={{ borderRadius: '10px', transition: { duration: 0.3 }, scale: 1.05 }}
                    >
                        <div className="w-40 h-4 bg-gray-300 rounded animate-pulse"></div>
                    </motion.div>
                ))}

            </div>
        </div>
    );
};

export default MenuLoadingSkeleton;
