import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import DailyNewsletter from "../pages/DailyNewsletter";
import WeeklyDigest from "../pages/WeeklyDigest";
import SearchResults from "../pages/SearchResults";

const AppRoutes: React.FC = () => {

    return (
        <Routes>
            <Route
                path="/"
                element={<DailyNewsletter />}
            />
            <Route
                path="/daily"
                element={<DailyNewsletter />}
            />
            <Route
                path="/weekly"
                element={<WeeklyDigest />}
            />
            <Route
                path="/search"
                element={<SearchResults />}
            />
            <Route path="*" element={<Navigate replace to="/" />} />
        </Routes>
    );
};

export default AppRoutes;