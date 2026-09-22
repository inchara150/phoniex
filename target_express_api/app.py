# server.js

function formatUserResponse(user_input) {
    if (user_input === null || user_input === undefined || user_input === '') {
        return 'UNKNOWN';
    }
    if (typeof user_input !== 'string') {
        user_input = String(user_input);
    }
    return user_input.toUpperCase();
}
