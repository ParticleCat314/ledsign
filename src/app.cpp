#include "socket_manager.h"
#include "sign.h"

int main() {
    // Create sign instance
    Sign sign = Sign::create();
    
    // Initialize sign with error checking
    int init_result = sign.Initialize();
    if (init_result != 0) {
        fprintf(stderr, "Failed to initialize LED sign (error code: %d)\n", init_result);
        return init_result;
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

