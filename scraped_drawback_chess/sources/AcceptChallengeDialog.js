import React from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogContentText,
    DialogActions,
    ThemeProvider,
    createTheme,
    Button,
} from '@mui/material';

import { fetchWrapper, playNotifySound } from './Helpers';
import { useNavigate } from 'react-router-dom';

const darkTheme = createTheme({
    palette: {
        mode: 'dark',
    },
});

export default function AcceptChallengeDialog({ open, handleClose, gameId, challengerDisplayName, friendshipId, username, fromPolling, abortCurrentGame, notifySound }) {
    const navigate = useNavigate();

    const onAcceptChallenge = () => {
        fetchWrapper(`/accept_challenge/${friendshipId}`, { gameId, username, ackNotNecessaryForAcceptor: fromPolling }, 'POST', 5050)
            .then((response) => {
                if (response.success) {
                    if (fromPolling) {
                        if (abortCurrentGame) {
                            abortCurrentGame();
                        }
                        if (notifySound) {
                            playNotifySound(notifySound, 100);
                        }
                        navigate(`/game/${response.game?.id}/${response.color === 'white' ? 'black' : 'white'}`);   
                        
                        // Reload the page to get the new game
                        window.location.reload();
                    }
                    handleClose();
                } else {
                    console.error(response.error);
                }
            })
    }

    const onDeclineChallenge = () => {
        fetchWrapper(`/decline_challenge`, { username }, 'POST', 5050)
            .then((response) => {
                if (response.success) {
                    handleClose();
                } else {
                    console.error(response.error);
                }
            })
    }

    return (
        <ThemeProvider theme={darkTheme}>
            <Dialog open={open} onClose={handleClose} PaperProps={{
                style: { backgroundColor: '#000033' },
            }}>
                <DialogTitle style={{ textAlign: 'center' }}>Challenge Received</DialogTitle>
                <DialogContent>
                    <DialogContentText style={{ textAlign: 'center' }}>
                        {`You have been challenged by ${challengerDisplayName}.`}
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button variant="contained" onClick={onAcceptChallenge}>Accept</Button>
                    <Button variant="contained" onClick={onDeclineChallenge}>Decline</Button>
                </DialogActions>
            </Dialog>
        </ThemeProvider>
    );
}