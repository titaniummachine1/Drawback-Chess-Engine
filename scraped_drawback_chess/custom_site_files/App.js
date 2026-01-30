import './App.css';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import { Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import GamePage from './GamePage';
import LandingPage from './LandingPage';
import RejoinQueuePage from './RejoinQueuePage';
import DrawbackGlossary from './DrawbackGlossary';
import MatchHistoryPage from './MatchHistoryPage';
import GeneratorPage from './GeneratorPage';
import LeaderboardPage from './LeaderboardPage';
import MissingPage from './MissingPage';
import ErrorBoundary from './ErrorBoundary';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
  },
});

function App() {
  // Define an array of paths that should be excluded from React routing
  const excludedPaths = [
    '/app1', 
    '/app2',
    '/app3',
    '/app4',
    '/app5',
    '/app6',
    '/app7',
    '/app8',
    '/app9',
    '/app10',
    '/app11',
    '/app12',
    '/app13',
    '/app14',
    '/app15',
    '/app16',
  ];

  // Function to check if the current path should be excluded
  const shouldExcludePath = () => {
    const currentPath = window.location.pathname;
    return excludedPaths.some(path => currentPath.startsWith(path));
  };

  return (
    <ThemeProvider theme={darkTheme}>
      <ErrorBoundary>
        {shouldExcludePath() ? null : (
          <Router>
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/rejoin_queue" element={<RejoinQueuePage />} />
              <Route path="/game/:id/:color" element={<GamePage />} />
              <Route path="/glossary" element={<DrawbackGlossary />} />
              <Route path="/glossary/all" element={<DrawbackGlossary showAll={true}/>} />
              <Route path="/friend/:friendshipId" element={<LandingPage />} />
              <Route path="/match-history" element={<Navigate to="/match-history/0" />} />
              <Route path="/match-history/:gameIndex" element={<MatchHistoryPage />} />
              <Route path="/leaderboard" element={<LeaderboardPage />} />
              <Route path="/generator" element={<GeneratorPage />} />
              <Route path="*" element={<MissingPage />} />
            </Routes>
          </Router>
        )}
      </ErrorBoundary>        
    </ThemeProvider>
  )
}

export default App;
