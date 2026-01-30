import React, { useState } from 'react';
import { TextField } from '@mui/material';
import Button from '@mui/material/Button';
import { fetchWrapper, getUsername } from './Helpers';
import Toast from './Toast';

export default function GeneratorPage() {
    let [error, setError] = useState(null);
    let [whiteElo, setWhiteElo] = useState(1200);
    let [blackElo, setBlackElo] = useState(1200);

    let [showWhite, setShowWhite] = useState(false);
    let [showBlack, setShowBlack] = useState(false);

    let [whiteDrawback, setWhiteDrawback] = useState(null);
    let [blackDrawback, setBlackDrawback] = useState(null);

    let username = getUsername(20);

    const showError = (message) => {
        setError(message);
        setTimeout(() => setError(null), 5000);
    }

    function generateGame() {
        fetchWrapper('/drawback_pair', { username, whiteElo: parseInt(whiteElo), blackElo: parseInt(blackElo) }, 'POST')
            .then(response => {
                if (response.success) {
                    setWhiteDrawback(response.white);
                    setBlackDrawback(response.black);
                } else {
                    showError(response.error);
                }
            });
    }

    return (
        <div>
            <div style={{ width: '100%', display: 'flex', justifyContent: 'center', position: 'fixed', left: 0, top: 10 }}>
                {error && <Toast message={error} onClose={() => setError(null)} />}
            </div>
            <h1>Game Generator</h1>
            <Button variant="contained" color="primary" onClick={generateGame}>
                Generate Game
            </Button>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
                <div style={{ dipslay: 'flex', flexDirection: 'column', marginRight: '20px' }}>
                    <h2>White Player</h2>
                    <div style={{ display: 'flex', alignItems: 'center', flexDirection: 'row' }}>
                        <TextField
                            value={whiteElo}
                            onChange={(e) => setWhiteElo(e.target.value)}
                            placeholder="Enter white player elo"
                            type="number"
                            inputMode="numeric"
                            pattern="[0-9]*"
                        />
                    </div>
                    {whiteDrawback && <div style={{ marginTop: '10px' }}>
                        <Button variant="contained" color="primary" onClick={() => setShowWhite(!showWhite)}>
                            {showWhite ? 'Hide' : 'Show'} Drawback
                        </Button>
                        {showWhite && <h2>{whiteDrawback}</h2>}
                    </div>
                    }
                </div>
                <div style={{ dipslay: 'flex', flexDirection: 'column' }}>
                    <h2>Black Player</h2>
                    <div style={{ display: 'flex', alignItems: 'center', flexDirection: 'row' }}>
                        <TextField
                            value={blackElo}
                            onChange={(e) => setBlackElo(e.target.value)}
                            placeholder="Enter black player elo"
                            type="number"
                            inputMode="numeric"
                            pattern="[0-9]*"
                        />
                    </div>
                    {blackDrawback && <div style={{ marginTop: '10px' }}>
                        <Button variant="contained" color="primary" onClick={() => setShowBlack(!showBlack)}>
                            {showBlack ? 'Hide' : 'Show'} Drawback
                        </Button>
                        {showBlack && <h2>{blackDrawback}</h2>}
                    </div>
                    }
                </div>
            </div>
        </div>
    );
}
