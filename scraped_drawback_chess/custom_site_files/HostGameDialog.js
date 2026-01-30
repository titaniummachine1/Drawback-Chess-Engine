import React, { useEffect, useState } from 'react';
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
    Select,
    MenuItem,
    FormControl,
    FormControlLabel,
    Switch,
    Slider,
    Grid,
    IconButton,
    Checkbox,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { fetchWrapper } from './Helpers';

const darkTheme = createTheme({
    palette: {
        mode: 'dark',
    },
});


export function HostGameDialog({ open, handleClose, username, showError, vsAi }) {
    const navigate = useNavigate();
    const [timeControl, setTimeControl] = useState('Real time');
    const [minutesPerSide, setMinutesPerSide] = useState(3);
    const [incrementInSeconds, setIncrementInSeconds] = useState(2);
    const [myDifficulty, setMyDifficulty] = useState("default");
    const [opponentDifficulty, setOpponentDifficulty] = useState("default");
    const [loading, setLoading] = useState(true);

    const [forbidWacky, setForbidWacky] = useState(localStorage.getItem('forbidWacky'));

    const [handicaps, setHandicaps] = useState(null);
    const [wackyHandicaps, setWackyHandicaps] = useState([]);

    let handicapChoices = handicaps?.filter(handicap => handicap.availability !== 'wacky')?.map(handicap => handicap.name);
    if (!forbidWacky && handicapChoices) {
        wackyHandicaps.forEach(handicap => handicapChoices.push(handicap));
    }

    // Sort handicapChoices alphabetically
    handicapChoices && handicapChoices.sort((a, b) => a.localeCompare(b));

    const [myChosenHandicap, setMyChosenHandicap] = useState("default");

    useEffect(() => {
        localStorage.setItem('forbidWacky', forbidWacky);
    }, [forbidWacky]);

    useEffect(() => {
        fetchWrapper('/handicap_glossary', { username }, 'GET')
            .then(response => {
                if (response.success) {
                    setHandicaps(response.handicaps);
                } else {
                    console.error('Error fetching data: ', response.error);
                }
            });
    }, []);

    useEffect(() => {
        fetchWrapper('/wacky_drawbacks', { username }, 'GET')
            .then((response) => {
                if (response.success) {
                    setWackyHandicaps(response.drawbacks);
                } else {
                    console.error('Error fetching data: ', response.error);
                }
            });
    }, []);

    useEffect(() => {
        fetchWrapper('/default_time_controls', { username }, 'GET')
            .then((response) => {
                if (response.success) {
                    if (response.timeControls) {
                        setMinutesPerSide(response.timeControls);
                        setIncrementInSeconds(response.increment);
                    } else {
                        setTimeControl('Unlimited');
                    }
                } else {
                    showError(response.error);
                }
                setLoading(false);
            });
    }, []);

    if (loading) {
        return null;
    }

    function newGame(color) {
        let whiteHandicap = localStorage.getItem('w-handicap');
        let blackHandicap = localStorage.getItem('b-handicap');
        let whiteParam = localStorage.getItem('w-param');
        let blackParam = localStorage.getItem('b-param');
        let stockfishDepth = localStorage.getItem('stockfish-depth');
        let endpoint = localStorage.getItem('dc-endpoint') || '/new_game';

        fetchWrapper(endpoint, {
            username,
            color,
            timeControls: timeControl === 'Real time' ? minutesPerSide * 60 : null,
            increment: incrementInSeconds,
            stockfish: vsAi,
            whiteHandicap: whiteHandicap, blackHandicap: blackHandicap,
            hostHandicap: myChosenHandicap,
            whiteParam,
            blackParam,
            stockfishDepth,
            myDifficulty: myDifficulty === 'default' ? null : myDifficulty,
            opponentDifficulty: opponentDifficulty === 'default' ? null : opponentDifficulty,
            allowWacky: !forbidWacky,
        }, 'POST')
            .then((response) => {
                if (response.success) {
                    navigate(`/game/${response.game.id}/${response.color}`);
                } else {
                    showError(response.error);
                }
            })
    }


    return (
        <ThemeProvider theme={darkTheme}>
            <Dialog open={open} onClose={handleClose} PaperProps={{
                style: { backgroundColor: '#000033' },
            }}>
                <DialogTitle style={{ textAlign: 'center' }}>Host game</DialogTitle>
                <DialogContent>
                    <Grid container direction="column" spacing={2} alignItems="center" justifyContent="center">
                        <Grid item>
                            <FormControl style={{ textAlign: 'center' }}>
                                <Typography style={{ marginBottom: '5px' }}>Time Control</Typography>
                                <Select value={timeControl} onChange={(e) => setTimeControl(e.target.value)}>
                                    <MenuItem value={"Real time"}>Real time</MenuItem>
                                    <MenuItem value={"Unlimited"}>Unlimited</MenuItem>
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid item>
                            <FormControl style={{ textAlign: 'center' }}>
                                {timeControl === "Real time" && (
                                    <div>
                                        <Typography>Minutes per side: {minutesPerSide}</Typography>
                                        <Slider value={minutesPerSide} onChange={(e, newValue) => setMinutesPerSide(newValue)} max={30} />
                                        <Typography style={{ width: '200px' }}>Increment in seconds: {incrementInSeconds}</Typography>
                                        <Slider value={incrementInSeconds} onChange={(e, newValue) => setIncrementInSeconds(newValue)} max={30} />
                                    </div>
                                )}
                            </FormControl>
                        </Grid>
                        <Grid item>
                            <FormControl style={{ textAlign: 'center' }}>
                                {handicapChoices && handicapChoices.length > 0 && <>
                                    <Typography style={{ marginBottom: '5px' }}>My drawback</Typography>
                                    <Select value={myChosenHandicap} onChange={(e) => setMyChosenHandicap(e.target.value)}>
                                        <MenuItem value={"default"}>Based on my difficulty</MenuItem>
                                        {(handicapChoices || []).map((handicap) => (
                                            <MenuItem value={handicap} key={handicap}>{handicap}</MenuItem>
                                        ))}
                                    </Select>
                                </>}
                            </FormControl>
                        </Grid>
                        <Grid item>
                            <FormControl style={{ textAlign: 'center' }}>
                                {myChosenHandicap === 'default' && <>
                                    <Typography style={{ marginBottom: '5px' }}>My difficulty</Typography>
                                    <Select value={myDifficulty} onChange={(e) => setMyDifficulty(e.target.value)}>
                                        <MenuItem value={"default"}>Based on my elo</MenuItem>
                                        <MenuItem value={"very easy"}>Very Easy</MenuItem>
                                        <MenuItem value={"easy"}>Easy</MenuItem>
                                        <MenuItem value={"medium"}>Medium</MenuItem>
                                        <MenuItem value={"hard"}>Hard</MenuItem>
                                        <MenuItem value={"very hard"}>Very Hard</MenuItem>
                                        <MenuItem value={"no drawback"}>No drawback</MenuItem>
                                    </Select>
                                </>}
                            </FormControl>
                        </Grid>
                        <Grid item>
                            <FormControl style={{ textAlign: 'center' }}>
                                <Typography style={{ marginBottom: '5px' }}>Opponent difficulty</Typography>
                                <Select value={opponentDifficulty} onChange={(e) => setOpponentDifficulty(e.target.value)}>
                                    <MenuItem value={"default"}>Based on their elo</MenuItem>
                                    <MenuItem value={"very easy"}>Very Easy</MenuItem>
                                    <MenuItem value={"easy"}>Easy</MenuItem>
                                    <MenuItem value={"medium"}>Medium</MenuItem>
                                    <MenuItem value={"hard"}>Hard</MenuItem>
                                    <MenuItem value={"very hard"}>Very Hard</MenuItem>
                                    <MenuItem value={"no drawback"}>No drawback</MenuItem>
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid item>
                            <FormControl style={{ maxWidth: '250px', textAlign: 'center' }}>
                                <FormControlLabel control={<Checkbox checked={!forbidWacky} onChange={(e) => setForbidWacky(!e.target.checked)} />} label="Allow wacky or experimental drawbacks" />
                            </FormControl>
                        </Grid>
                    </Grid>
                    <Grid container justifyContent="center">
                        <IconButton onClick={() => newGame('white')}>
                            <img src={`${process.env.PUBLIC_URL}/assets/white-king.png`} alt="White King" style={{ width: '50px', height: '50px' }} />
                        </IconButton>
                        <IconButton onClick={() => newGame('random')}>
                            <img src={`${process.env.PUBLIC_URL}/assets/half-king.png`} alt="Half King" style={{ width: '75px', height: '75px' }} />
                        </IconButton>
                        <IconButton onClick={() => newGame('black')}>
                            <img src={`${process.env.PUBLIC_URL}/assets/black-king.png`} alt="Black King" style={{ width: '50px', height: '50px' }} />
                        </IconButton>
                    </Grid>
                </DialogContent>
            </Dialog>
        </ThemeProvider>
    );
}