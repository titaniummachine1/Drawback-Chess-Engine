import React, { useState, useEffect , useRef } from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogContentText,
    createTheme,
    ThemeProvider,
    Typography,
    DialogActions,
    Button,
} from '@mui/material';
import { NavigationType, useNavigate } from 'react-router-dom';
import { fetchWrapper } from './Helpers';
import { baseURL } from './Settings';
import ClipboardJS from 'clipboard';

function log(str) {
    if (localStorage.getItem('log')) {
        console.log(str);
    }
}


const darkTheme = createTheme({
    palette: {
        mode: 'dark',
    },
});

function CopyButton({ text }) {
    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(text);
            log('success, copied to clipboard: ' + text);
        } catch (err) {
            log('Error copying to clipboard: ', err);
        }
    };

    return (
        <Button onClick={handleCopy} style={{ textTransform: 'none' }}>
            {text}
        </Button>
    );
}

export function FriendLinkDialog({ open, handleClose, username }) {
    const [friendshipId, setFriendshipId] = useState(null);

    useEffect(() => {
        fetchWrapper('/friendships', { username }, 'POST')
            .then(response => {
                if (response.success) {
                    setFriendshipId(response.friendshipId);
                }
            });
    }, [])

    return (
        <ThemeProvider theme={darkTheme}>
            <Dialog open={open} onClose={handleClose} PaperProps={{
                style: { backgroundColor: '#000033' },
            }}>
                <DialogTitle style={{ textAlign: 'center' }}>Add Friend</DialogTitle>
                {friendshipId != null ? <>
                    <DialogContent>
                        <DialogContentText style={{ textAlign: 'center' }}>
                            To add someone else as a friend, send them this link: <br />
                            <CopyButton text={`${baseURL}/friend/${friendshipId}`}/>
                        </DialogContentText>
                    </DialogContent>
                    <DialogActions>
                        <Button variant="contained" onClick={handleClose}>
                            Ok
                        </Button>
                    </DialogActions>
                </> : null}
            </Dialog>
        </ThemeProvider>
    );
}

export function AddFriendDialog({ open, handleClose, friendshipId, username, showMessage, showError }) {
    const [friendDisplayName, setFriendDisplayName] = useState(null);
    const navigate = useNavigate();

    useEffect(() => {
        fetchWrapper(`/display_name/${friendshipId}`, { username }, 'GET')
            .then(response => {
                if (response.success) {
                    setFriendDisplayName(response.displayName);
                } else {
                    showError(response.error);
                    handleClose();
                    navigate('/');
                }
            });
    })

    if (!friendDisplayName) {
        return null;
    }

   const handleAccept = () => {
        fetchWrapper('/form_friendship', { username, friendshipId }, 'POST')
            .then(response => {
                if (response.success) {
                    handleClose();
                    navigate('/');
                    showMessage('Friend added!')
                } else {
                    showError(response.error);
                    handleClose();
                    navigate('/');
                }
            });

    }

    const handleCloseAndNavigate = () => {
        handleClose();
        navigate('/');
    }

    return (
        <ThemeProvider theme={darkTheme}>
            <Dialog open={open} onClose={handleClose} PaperProps={{
                style: { backgroundColor: '#000033' },
            }}>
                <DialogTitle style={{ textAlign: 'center' }}>Add Friend</DialogTitle>
                <DialogContent>
                    <DialogContentText style={{ textAlign: 'center' }}>
                        {friendDisplayName} would like to add you as a friend!
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button variant="contained" onClick={handleAccept}>
                        Accept
                    </Button>
                    <Button variant="contained" onClick={handleCloseAndNavigate}>
                        Decline
                    </Button>
                </DialogActions>
            </Dialog>
        </ThemeProvider>
    );
}