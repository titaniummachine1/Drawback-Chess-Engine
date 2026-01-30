import React, { useState } from 'react';
import {
    Dialog,
    DialogTitle,
    DialogActions,
    ThemeProvider,
    createTheme,
    Button,
    TextField,
    DialogContent,
    DialogContentText,
    Grid,
} from '@mui/material';
import { fetchWrapper } from './Helpers';

const darkTheme = createTheme({
    palette: {
        mode: 'dark',
    },
});

const buttonStyles = {
    '&:hover': {
        backgroundColor: '#000033',
    },
    minHeight: '100px',
}

export default function SeedEloDialog({ open, handleClose, username , showError }) {
    const [playerClaimedElo, setPlayerClaimedElo] = useState('');

    const seedElo = (rawElo) => {
        if (!rawElo || isNaN(rawElo)) {
            showError('Please enter a valid number for Elo.');
        } else {
            let elo = parseInt(rawElo);
            elo = Math.min(2000, Math.max(400, elo));
    
            fetchWrapper(`/seed_elo`, { username, elo }, 'POST')
                .then((response) => {
                    if (response.success) {
                        handleClose();
                    } else {
                        showError(response.error);
                        handleClose();
                    }
                });
        }
    }

    return (
        <ThemeProvider theme={darkTheme}>
            <Dialog open={open} onClose={handleClose} PaperProps={{
                style: { backgroundColor: '#000033' },
            }}>
                <DialogTitle style={{ textAlign: 'center'}}>Welcome!</DialogTitle>
                <DialogContent> 
                    {/* <DialogContentText style={{ textAlign: 'center', fontWeight: 'bold', fontSize: '1.2rem' }}>
                        If you haven't played before, you should probably read <span style={{ color: '#1E90FF', cursor: 'pointer' }} onClick={() => setHowToPlayDialogOpen(true)}>How To Play</span> - there are some important rules differences between this and chess!
                    </DialogContentText> */}
                    <Grid item container direction="column" justifyContent="center" alignItems="center" spacing={3}>
                        <Grid item>
                            <DialogContentText style={{textAlign: 'center'}}>
                                If you know your approximate elo (from chess.com, lichess, USCF, FIDE, etc), please enter it here, and we will use it to determine your starting elo.
                                (Players with higher elos will get tougher drawbacks than their opponents, so if you enter a big number here, be prepared for a challenge!)
                            </DialogContentText>
                        </Grid>
                        <Grid item>
                            <TextField 
                                value={playerClaimedElo}
                                onChange={(e) => setPlayerClaimedElo(e.target.value)}
                                // style={{ width: '100%', textAlign: 'center' }}
                                placeholder="Enter your elo here" 
                                type="number"
                                inputMode="numeric"
                                pattern="[0-9]*"
                            />
                        </Grid>
                        <Grid item>
                            <Button
                                variant="contained"
                                onClick={() => seedElo(playerClaimedElo)}
                            >
                                Submit Elo
                            </Button>
                        </Grid>
                        <Grid item>
                            <DialogContentText style={{textAlign: 'center'}}>
                                If you don't know your elo or are new to chess, you can also click one of the buttons below indicating your level to get started.
                            </DialogContentText>
                        </Grid>
                    </Grid>
                </DialogContent>
                <DialogActions style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 10 }}>
                    <Button variant="contained" onClick={() => seedElo(600)}>New to Chess</Button>
                    <Button variant="contained" onClick={() => seedElo(900)}>Beginner</Button>
                    <Button variant="contained" onClick={() => seedElo(1200)}>Intermediate</Button>
                </DialogActions>
            </Dialog>
        </ThemeProvider>
    );
}