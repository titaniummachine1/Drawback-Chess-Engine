import React, { useState } from 'react';
import { 
    Dialog, 
    DialogTitle, 
    DialogContent, 
    DialogContentText, 
    Checkbox, 
    FormControlLabel, 
    createTheme, 
    ThemeProvider, 
    Slider, 
    Typography,
    DialogActions,
    Button,
} from '@mui/material';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
  },
});

export default function SettingsDialog({ 
    open,
    handleClose, 
    neverPremoveIntoCheck, 
    setNeverPremoveIntoCheck, 
    volume, 
    setVolume,
    alwaysPromoteToQueen,
    setAlwaysPromoteToQueen,
    centerBoard,
    setCenterBoard,
    castleViaRook,
    setCastleViaRook,
    showHighlights,
    setShowHighlights,
}) {
    const handleCheckChange = (event) => {
        setNeverPremoveIntoCheck(event.target.checked);
    };

    const handleVolumeChange = (event, newValue) => {
        setVolume(newValue);
    };

    const handleAlwaysPromoteToQueenChange = (event) => {
        setAlwaysPromoteToQueen(event.target.checked);
    }

    const handleCenterBoardChange = (event) => {
        setCenterBoard(event.target.checked);
    }

    const handleCastleViaRookChange = (event) => {
        setCastleViaRook(event.target.checked);
    }

    const handleShowHighlightsChange = (event) => {
        setShowHighlights(event.target.checked);
    }

    return (
        <ThemeProvider theme={darkTheme}>
            <Dialog open={open} onClose={handleClose} PaperProps={{ 
                    style: { backgroundColor: '#000033' }, 
                }}>
                <DialogTitle>Game Settings</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        <FormControlLabel
                            control={
                                <Checkbox
                                    checked={neverPremoveIntoCheck}
                                    onChange={handleCheckChange}
                                    name="neverPremoveIntoCheck"
                                    color="primary"
                                />
                            }
                            label="Never premove into check"
                        />
                    </DialogContentText>
                    <br />
                    <DialogContentText>
                        <FormControlLabel
                            control={
                                <Checkbox
                                    checked={alwaysPromoteToQueen}
                                    onChange={handleAlwaysPromoteToQueenChange}
                                    name="alwaysPromoteToQueen"
                                    color="primary"
                                />
                            }
                            label="Always promote to queen"
                        />
                    </DialogContentText>
                    <br />
                    <DialogContentText>
                        <FormControlLabel
                            control={
                                <Checkbox
                                    checked={centerBoard}
                                    onChange={handleCenterBoardChange}
                                    name="centerBoard"
                                    color="primary"
                                />
                            }
                            label="Center board"
                        />
                    </DialogContentText>
                    <br />
                    <DialogContentText>
                        <FormControlLabel
                            control={
                                <Checkbox
                                    checked={castleViaRook}
                                    onChange={handleCastleViaRookChange}
                                    name="castleViaRook"
                                    color="primary"
                                />
                            }
                            label="Castle by clicking on king then rook"
                        />
                    </DialogContentText>
                    <br />
                    <DialogContentText>
                        <FormControlLabel
                            control={
                                <Checkbox
                                    checked={showHighlights}
                                    onChange={handleShowHighlightsChange}
                                    name="showHighlights"
                                    color="primary"
                                />
                            }
                            label="Show highlights"
                        />
                    </DialogContentText>
                    <DialogContentText>
                        <Typography id="volume-slider" gutterBottom>
                            Volume
                        </Typography>
                        <Slider
                            value={volume}
                            onChange={handleVolumeChange}
                            aria-labelledby="volume-slider"
                            valueLabelDisplay="auto"
                            step={1}
                            marks
                            min={0}
                            max={100}
                        />
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button variant="contained" onClick={handleClose}>Ok</Button>
                </DialogActions>
            </Dialog>
        </ThemeProvider>
    );
}