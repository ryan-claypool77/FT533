from waitress import serve
import hw2_rc

serve(hw2_rc.server, port=80)
