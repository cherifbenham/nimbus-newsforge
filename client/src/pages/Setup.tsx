import React, { useEffect, useState } from 'react';
import axios from 'axios';
import config from '../config/apiService';

const Setup: React.FC = () => {
  const [prompt, setPrompt] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [status, setStatus] = useState<string>('');

  useEffect(() => {
    const fetchPrompt = async () => {
      try {
        setLoading(true);
        const res = await axios.get(`${config.url.API_URL}/compose-weekly/prompt`);
        setPrompt(res.data.prompt || '');
      } catch (e) {
        setStatus('Failed to load prompt');
      } finally {
        setLoading(false);
      }
    };
    fetchPrompt();
  }, []);

  const handleSave = async () => {
    try {
      setLoading(true);
      await axios.put(`${config.url.API_URL}/compose-weekly/prompt`, { prompt });
      setStatus('Saved');
      setTimeout(() => setStatus(''), 1500);
    } catch (e) {
      setStatus('Save failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-auto bg-gray-50 dark:bg-slate-900 text-gray-900 dark:text-slate-100">
      <div className="max-w-4xl mx-auto p-6 space-y-4">
        <h1 className="text-2xl font-semibold">Compose Weekly Setup</h1>
        <p className="text-sm text-gray-600 dark:text-slate-300">
          Customize additional instructions used by Gemini when generating classification, comments, and scoring.
          These instructions are appended to the default system prompt.
        </p>

        <textarea
          className="w-full min-h-[300px] p-4 rounded-md border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800"
          placeholder="Add scoring and relevance guidance..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />

        <div className="flex items-center space-x-3">
          <button
            onClick={handleSave}
            disabled={loading}
            className="px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Saving...' : 'Save'}
          </button>
          {status && <span className="text-sm text-gray-600 dark:text-slate-300">{status}</span>}
        </div>
      </div>
    </div>
  );
};

export default Setup;

