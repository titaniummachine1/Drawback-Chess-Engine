import React, { useState, useEffect } from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogContentText,
    DialogActions,
    ThemeProvider,
    createTheme,
    Button,
    TextField,
    FormControl,
    FormControlLabel,
    Grid,
    InputAdornment,
    Checkbox,
} from '@mui/material';
import IconButton from '@mui/material/IconButton';
import ModeEditIcon from '@mui/icons-material/ModeEdit';
import DeleteIcon from '@mui/icons-material/Delete';
import { fetchWrapper } from './Helpers';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';

const darkTheme = createTheme({
    palette: {
        mode: 'dark',
    },
});

function NameEditor({ handleClose, username , showError }) {
    let [newName, setNewName] = useState('');

    function submit() {
        fetchWrapper('/username', { username, displayName: newName }, 'POST')
            .then((response) => {
                if (response.success) {
                    handleClose();
                } else {
                    showError(response.error);
                }
            })
    }

    function handleKeyDown(e) {
        if (e.key === 'Enter') {
            submit();
        } else if (e.key === 'Escape') {
            handleClose();
        }
    }

    useEffect(() => {
        document.querySelector('input').focus();
    }, []);

    return (
        <ThemeProvider theme={darkTheme}>
            <DialogContent>
                <DialogContentText style={{ textAlign: 'center' }}>
                    <TextField value={newName} onChange={(e) => setNewName(e.target.value)} onKeyDown={handleKeyDown} label={'New display name'} />
                </DialogContentText>
            </DialogContent>
            <DialogActions>
                <Button variant="outlined" onClick={submit}>Submit</Button>
                <Button variant="outlined" onClick={handleClose}>Cancel</Button>
            </DialogActions>
        </ThemeProvider>
    );
}

function Friend({ name, unfriend }) {
    return (
        <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', marginBottom: '10px' }}>
            <DialogContentText style={{ textAlign: 'center', fontSize: '18px' }}>{name}</DialogContentText>
            <Button variant="outlined" style={{ marginLeft: '20px', 'height': '30px', borderRadius: '15%'}} onClick={unfriend}>
                <DeleteIcon fontSize="small" />
            </Button>
        </div>
    );
}

function Friends({ friends, username, update }) {
    function unfriend(friendship, username) {
        fetchWrapper('/unfriend', { username, friendship }, 'POST')
            .then((response) => {
                if (response.success) {
                    update();
                } else {
                    console.error(response.error);
                }
            })
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', flexWrap: 'wrap', justifyContent: 'center', alignItems: 'center' }}>
            {friends.map((friend, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', margin: '10px' }}>
                    <Friend name={friend.displayName} unfriend={() => unfriend(friend.key, username)} />
                </div>
            ))}
        </div>
    );
}

function PasswordField({ password, setPassword, showPassword, setShowPassword, onKeyDown, label}) {
    return (
        <TextField
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={onKeyDown || (() => {})}
            label={label || 'Password'}
            type={showPassword ? 'text' : 'password'}
            InputProps={{
                endAdornment: (
                    <InputAdornment position="end">
                        <IconButton
                            aria-label="toggle password visibility"
                            onClick={() => setShowPassword(!showPassword)}
                            onMouseDown={(e) => e.preventDefault()}
                        >
                            {showPassword ? <Visibility /> : <VisibilityOff />}
                        </IconButton>
                    </InputAdornment>
                ),
            }}
        />
    );
}

function LoginDialog({ open, handleClose, username, showMessage, showError }) {
    let [loginUsername, setLoginUsername] = useState('');
    let [password, setPassword] = useState('');
    let [showPassword, setShowPassword] = useState(false);

    function submit() {
        fetchWrapper('/login', { username: loginUsername, password }, 'POST')
            .then((response) => {
                if (response.success) {
                    localStorage.setItem('dc-username', response.userToken);
                    showMessage('Logged in!');
                    setTimeout(() => {
                        window.location.reload();
                    }, 500);
                } else {
                    showError(response.error);
                }
            }
        )
    }

    function handleKeyDown(e) {
        if (e.key === 'Enter') {
            submit();
        } else if (e.key === 'Escape') {
            handleClose();
        }
    }

    return (
        <ThemeProvider theme={darkTheme}>
            <Dialog open={open} onClose={handleClose} PaperProps={{
                style: { backgroundColor: '#000033', width: '500px', maxWidth: '100%' },
            }}>
                <DialogTitle style={{ textAlign: 'center', fontSize: '24px' }}>Log In</DialogTitle>
                <DialogContent>
                    <br />
                    <DialogContentText style={{ textAlign: 'center', marginBottom: '20px', fontSize: '20px' }}>
                        <TextField value={loginUsername} onChange={(e) => setLoginUsername(e.target.value)} onKeyDown={handleKeyDown} label={'Username'} />
                    </DialogContentText>
                    <br />
                    <DialogContentText style={{ textAlign: 'center', marginBottom: '20px', fontSize: '20px' }}>
                        <PasswordField
                            password={password}
                            setPassword={setPassword}
                            showPassword={showPassword}
                            setShowPassword={setShowPassword}
                            onKeyDown={handleKeyDown}
                            label={'Password'}
                        />
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button variant="outlined" onClick={submit}>Submit</Button>
                    <Button variant="outlined" onClick={handleClose}>Cancel</Button>
                </DialogActions>
            </Dialog>
        </ThemeProvider>
    );
}

function CreateAccountDialog({open, handleClose, username, showMessage, showError, playerInfo, setPlayerInfo}) {
    let [loginUsername, setLoginUsername] = useState('');
    let [password, setPassword] = useState('');
    let [showPassword, setShowPassword] = useState(false);
    let [confirmPassword, setConfirmPassword] = useState('');
    let [showConfirmPassword, setShowConfirmPassword] = useState(false);

    function submit() {
        if (password !== confirmPassword) {
            showError("Passwords don't match");
            return;
        }

        fetchWrapper('/create_login_info', { username, loginInfoUsername: loginUsername, password }, 'POST')
            .then((response) => {
                if (response.success) {
                    showMessage('Account created!');
                    setPlayerInfo({...playerInfo, loginUsername});
                    handleClose();
                } else {
                    showError(response.error);
                }
            })
    }

    function handleKeyDown(e) {
        if (e.key === 'Enter') {
            submit();
        } else if (e.key === 'Escape') {
            handleClose();
        }
    }

    return (
        <ThemeProvider theme={darkTheme}>
            <Dialog open={open} onClose={handleClose} PaperProps={{
                style: { backgroundColor: '#000033', width: '500px', maxWidth: '100%' },
            }}>
                <DialogTitle style={{ textAlign: 'center', fontSize: '24px' }}>Create Account</DialogTitle>
                <DialogContent>
                    <br />
                    <DialogContentText style={{ textAlign: 'center', marginBottom: '20px', fontSize: '20px' }}>
                        <TextField value={loginUsername} onChange={(e) => setLoginUsername(e.target.value)} onKeyDown={handleKeyDown} label={'Username'} />
                    </DialogContentText>
                    <DialogContentText style={{ textAlign: 'center', marginBottom: '20px', fontSize: '16px' }}>
                        Your username need not be the same as your display name, but it must not be already taken. Your display name is what will be displayed
                        to your opponents; your username is what you will use to log in.
                    </DialogContentText>
                    <br />
                    <DialogContentText style={{ textAlign: 'center', marginBottom: '20px', fontSize: '20px' }}>
                        <PasswordField 
                            password={password} 
                            setPassword={setPassword} 
                            showPassword={showPassword} 
                            setShowPassword={setShowPassword} 
                            onKeyDown={handleKeyDown} 
                            label={'Password'} 
                        />
                    </DialogContentText>
                    <DialogContentText style={{ textAlign: 'center', marginBottom: '20px', fontSize: '20px' }}>
                        <PasswordField
                            password={confirmPassword}
                            setPassword={setConfirmPassword}
                            showPassword={showConfirmPassword}
                            setShowPassword={setShowConfirmPassword}
                            onKeyDown={handleKeyDown}
                            label={'Confirm Password'}
                        />
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button variant="outlined" onClick={submit}>Submit</Button>
                    <Button variant="outlined" onClick={handleClose}>Cancel</Button>
                </DialogActions>
            </Dialog>
        </ThemeProvider>
    );
}

export default function PlayerInfo({ open, handleClose, username, showMessage, showError, rememberTimePreference, setRememberTimePreference }) {
    let [playerInfo, setPlayerInfo] = useState(null);
    let [editingName, setEditingName] = useState(false);
    let [createAccountDialogOpen, setCreateAccountDialogOpen] = useState(false);
    let [loginDialogOpen, setLoginDialogOpen] = useState(false);

    function update() {
        fetchWrapper('/username', { username }, 'GET')
            .then((response) => {
                if (response.success) {
                    setPlayerInfo(response.user);
                } else {
                    console.error(response.error);
                }
            })
    }

    useEffect(() => {
        update();
    }, [username]);

    const handleLogOut = () => {
        localStorage.removeItem('dc-username');
        window.location.reload();
    }

    let name = playerInfo?.displayName;
    let elo = playerInfo?.elo;
    let gamesPlayed = playerInfo?.gamesPlayed;
    let friends = playerInfo?.friends;

    if (!playerInfo) {
        return null;
    }

    const showHidden = !!localStorage.getItem('showHidden')

    return (
        <ThemeProvider theme={darkTheme}>
            <Dialog open={open} onClose={handleClose} PaperProps={{
                style: { backgroundColor: '#000033', width: '500px', maxWidth: '100%' },
            }}>
                <DialogTitle style={{ textAlign: 'center', fontSize: '24px' }}>Player Info</DialogTitle>
                <DialogContent>
                    <DialogContentText style={{ textAlign: 'center', marginBottom: '20px', fontSize: '20px' }}>
                        {`Display Name: `}
                        <span style={{ fontWeight: 'bold' }}>{name || "Anonymous"}</span>
                        <Button 
                            variant="outlined" 
                            style={{ 
                                marginLeft: '20px', 
                                height: '30px', // Set the height to make the button smaller
                                borderRadius: '15%', // Apply border-radius to make the button circular
                            }} 
                            onClick={() => setEditingName(true)}
                        >
                            <ModeEditIcon />
                        </Button>
                    </DialogContentText>
                    {editingName && <NameEditor showError={showError} handleClose={() => { setEditingName(false); update() }} username={username} />}
                    {editingName && <>
                        <br />
                        <br />
                    </>}
                    <DialogContentText style={{ textAlign: 'center', fontSize: '18px' }}>
                        {`Elo: `}
                        <span style={{ fontWeight: 'bold' }}>{`${elo}`}</span>
                    </DialogContentText>
                    <DialogContentText style={{ textAlign: 'center', fontSize: '18px' }}>
                        {`Games Played: `}
                        <span style={{ fontWeight: 'bold' }}>{`${gamesPlayed}`}</span>
                    </DialogContentText>
                    <br />
                    <FormControl style={{ display: 'flex', alignItems: 'center', textAlign: 'center' }}>
                        <FormControlLabel
                            control={
                                <Checkbox
                                    checked={rememberTimePreference}
                                    onChange={() => setRememberTimePreference(!rememberTimePreference)}
                                    color="primary"
                                />
                            }
                            label="Skip time preference dialog for queuing"
                            labelPlacement="bottom"
                        />
                    </FormControl>
                    <br />
                    {friends && friends.length > 0 &&
                        <DialogContent>
                            <DialogContentText style={{ textAlign: 'center', fontSize: '18px' }}>
                                {`Friends:`}
                            </DialogContentText>
                            <Friends friends={friends} username={username} update={update} />
                        </DialogContent>}

                    <br />
                    {playerInfo?.loginUsername ? <Grid container justifyContent="center" alignItems="center" direction="column" spacing={2}>
                        <Grid item>
                            <DialogContentText style={{ textAlign: 'center', fontSize: '18px' }}>
                                {`Username: `}
                                <span style={{ fontWeight: 'bold' }}>{`${playerInfo.loginUsername}`}</span>
                            </DialogContentText>
                        </Grid>
                        <Grid item>
                            <Button variant="outlined" style={{ display: 'flex', justifyContent: 'center' }} onClick={handleLogOut}>
                                Log out
                            </Button>
                        </Grid>
                    </Grid> : <Grid container justifyContent="center" alignItems="center" spacing={2}>
                        <Grid item>
                            <Button variant="outlined" style={{ display: 'flex', justifyContent: 'center' }} onClick={() => setCreateAccountDialogOpen(true)}>
                                Create account (optional)
                            </Button>
                        </Grid>
                        <Grid item>
                            <DialogContentText style={{ textAlign: 'center', fontSize: '16px'}}>
                                Creating an account is helpful if you want to migrate your account to another device,
                                or if you want your account information to persist even after clearing your browser's
                                cache. Otherwise, you don't need to create an account.
                            </DialogContentText>
                        </Grid>
                        <Grid item>
                            <Button variant="outlined" style={{ display: 'flex', justifyContent: 'center' }} onClick={() => setLoginDialogOpen(true)}>
                                Log in (optional)
                            </Button>
                        </Grid>
                        <Grid item>
                            <DialogContentText style={{ textAlign: 'center', fontSize: '16px'}}>
                                If you've already created an account somewhere else, you can log in here to
                                recover your account information. <b>Warning:</b> if you log into a 
                                different account and you haven't already created an account for the games you've played
                                on this device, you will lose access to them.
                            </DialogContentText>
                        </Grid>
                    </Grid>}
                </DialogContent>
                <DialogActions>
                    <Button variant="contained" onClick={handleClose}>Close</Button>
                </DialogActions>
            </Dialog>
            {createAccountDialogOpen && <CreateAccountDialog open={createAccountDialogOpen} handleClose={() => setCreateAccountDialogOpen(false)} username={username} showMessage={showMessage} showError={showError} playerInfo={playerInfo} setPlayerInfo={setPlayerInfo} />}
            {loginDialogOpen && <LoginDialog open={loginDialogOpen} handleClose={() => setLoginDialogOpen(false)} username={username} showMessage={showMessage} showError={showError} />}
        </ThemeProvider>
    );
}