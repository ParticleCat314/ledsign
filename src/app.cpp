#include "socket_manager.h"
#include "sign.h"

int main() {
    // Create sign instance
    Sign sign;
    
    // Initialize sign with error checking
    SignError init_result = sign.Initialize();
    if (init_result != SignError::SUCCESS) {
        fprintf(stderr, "Failed to initialize LED sign (error code: %d)\n", static_cast<int>(init_result));
        return static_cast<int>(init_result);
    }
    
    sign.clear();
    
    // Run socket server
    int server_result = run_socket_server(sign);
    if (server_result != 0) {
        fprintf(stderr, "Socket server exited with error code: %d\n", server_result);
        return server_result;
    }
    
    return 0;
}

