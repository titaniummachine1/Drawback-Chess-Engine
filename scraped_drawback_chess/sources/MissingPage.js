import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import Button from '@mui/material/Button';

export default function MissingPage() {
    return (
        <div>
            <h1>404</h1>
            <p>Page not found</p>
            <Button variant="contained" color="primary" component={Link} to="/">Return to home page</Button>
        </div>
    );
}