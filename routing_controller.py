#SPIW PROJ 1
#Kacper Jez
#Jakub Sulikowski
#Michal Filipczyk

from json import load
from turtle import pos
from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpidToStr
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.packet.arp import arp
from pox.lib.packet.ethernet import ethernet, ETHER_BROADCAST
from pox.lib.packet.packet_base import packet_base
from pox.lib.packet.packet_utils import *
import pox.lib.packet as pkt
from pox.lib.recoco import Timer
import time
from pox.openflow.of_json import *
import struct

log = core.getLogger()

s1_dpid=0
s2_dpid=0
s3_dpid=0
s4_dpid=0
s5_dpid=0

# pomiary s1-s2
s1s2_start_time = 0.0
s1s2_sent_time1 = 0.0
s1s2_sent_time2 = 0.0
s1s2_received_time1 = 0.0
s1s2_received_time2 = 0.0
s1s2_mytimer = 0
s1s2_OWD1 = 0.0
s1s2_OWD2 = 0.0
s1s2_src_dpid = 0
s1s2_dst_dpid = 0

s1s2_delay = 0

# pomiary s1-s3
s1s3_start_time = 0.0
s1s3_sent_time1 = 0.0
s1s3_sent_time2 = 0.0
s1s3_received_time1 = 0.0
s1s3_received_time2 = 0.0
s1s3_mytimer = 0
s1s3_OWD1 = 0.0
s1s3_OWD2 = 0.0
s1s3_src_dpid = 0
s1s3_dst_dpid = 0

s1s3_delay = 0

# pomiary s1-s4
s1s4_start_time = 0.0
s1s4_sent_time1 = 0.0
s1s4_sent_time2 = 0.0
s1s4_received_time1 = 0.0
s1s4_received_time2 = 0.0
s1s4_mytimer = 0
s1s4_OWD1 = 0.0
s1s4_OWD2 = 0.0
s1s4_src_dpid = 0
s1s4_dst_dpid = 0

s1s4_delay = 0





# probe protocol packet definition; only timestamp field is present in the header (no payload part)
class myproto( packet_base ):

  def __init__( self ):
    packet_base.__init__( self )
    self.timestamp=0

  def hdr( self, payload ):
    return struct.pack( '!I', self.timestamp ) # code as unsigned int (I), network byte order (!, big-endian - the most significant byte of a word at the smallest memory address)

#klasa intentow
class Intent():
  def __init__( self, source_host, destination_host, delay, capacity ):
    self.source_host = source_host
    self.destination_host = destination_host
    self.delay = delay
    self.capacity = capacity  
    self.flow_id = 1  

#klasa flowow
class Flow():
  def __init__( self, id, switch, src, dst, load ):
    self.switch = id
    self.switch = switch
    self.src = src
    self.dst = dst
    self.load = load

#klasa routing kontroller
class RoutingController():
  def __init__( self ):
    self.get_state_of_links() 
    #lista flowow
    self.flows = []
    self.flow_id = 1
  
  #dodawanie do listy flowow 
  def add_flow( self, switch, src, dst, load = 100 ):
    self.flows.append( Flow(self.flow_id, switch, src, dst, load) )
    self.flow_id = self.flow_id + 1

  def get_state_of_links( self ):
    self.links_state = {
    "s2": s1s2_delay,
    "s3": s1s3_delay,
    "s4": s1s4_delay
    }
  
  def update( self, intent ):
    print "------------------------------------------------------------------------------------"
    print "RoutingController: zaaktualizowano informacje o laczach"
    self.get_state_of_links()
    print "\nRoutingController: opoznienie pomiedzy h1 a switchem {} \n".format( routingController.links_state )
    self.routing( intent )
    

  #--------Glowna funkcja ustawiania flowow na podstawie intentow--------
  def routing( self, intents ):
    number_of_flows = {"s2": 0, "s3": 0, "s4": 0}
    loads_of_links = {"s2": 0, "s3": 0, "s4": 0}

    #ustawianie flowow dla kazdego intenta
    for intent in intents:
      possible_flows = []
      for _, ( name_switch, delay ) in enumerate( self.links_state.items() ):
        #wybieranie mozliwych sciezek na podstawie delayu
        if delay < int( intent.delay ):
          possible_flows.append( name_switch )
          

      result = "(INTENT) src: {}, dst: {}, required_delay: {}, possible_flows: {}".format( intent.source_host, intent.destination_host, intent.delay, possible_flows )
      #Jezeli zadne lacze nie spelnia intentu to routowanie bez QoS
      if len( possible_flows ) == 0:
        result = result + " routing bez zapewnienia QoS! "
        possible_flows = ["s2", "s3", "s4"]


      for f in self.flows:
        number_of_flows[f.switch] = number_of_flows[f.switch] + 1
        loads_of_links[f.switch] = loads_of_links[f.switch] + f.load

      
      switch = self.link_select( possible_flows, number_of_flows, loads_of_links )
      result = result + " wyslano przez: {}".format( switch )


      self.msg( intent.source_host, intent.destination_host, switch )    


      self.add_flow( switch, intent.source_host, intent.destination_host, intent.capacity )
      number_of_flows = {"s2": 0, "s3": 0, "s4": 0}
      loads_of_links = {"s2": 0, "s3": 0, "s4": 0}
      for f in self.flows:
        number_of_flows[f.switch] = number_of_flows[f.switch] + 1
        loads_of_links[f.switch] = loads_of_links[f.switch] + f.load

      print result


    print "\nRoutingController: Alokacja Flowow {}".format( number_of_flows )
    print "RoutingController: Alokacja obciazenia {}\n".format( loads_of_links )
    del self.flows[:]


  def link_select( self, possible_flows, number_of_flows, loads_of_links ):
    min = number_of_flows[possible_flows[0]]
    min_id = possible_flows[0]

    for flow in possible_flows[1:]:
      if number_of_flows[flow] < min: 
          min = number_of_flows[flow]
          min_id = flow
      if number_of_flows[flow] == min:
        if loads_of_links[flow] < loads_of_links[min_id]:
          min = number_of_flows[flow]
          min_id = flow


    return min_id

    #tworzenie konstrukcji flowa
  def msg( self, source_host, destination_host, switch ):
    flow_table ={'s2': 5, 's3': 6, 's4': 4}
    src_hosts = {'h1': s1_dpid, 'h2': s2_dpid, 'h3': s3_dpid}


    core.openflow.getConnection( src_hosts[source_host] ).send( of.ofp_stats_request(body=of.ofp_port_stats_request()) )


    msg = of.ofp_flow_mod()
    msg.command=of.OFPFC_MODIFY_STRICT
    msg.priority =100
    msg.idle_timeout = 0
    msg.hard_timeout = 0
    msg.match.dl_type = 0x0800
    msg.match.nw_dst = destination_host
    msg.actions.append( of.ofp_action_output(port = int(flow_table[switch])) )


    core.openflow.getConnection( src_hosts[source_host] ).send( msg )
    
 
def getTheTime():  #funkcja tworzaca timestamp
  flock = time.localtime()
  then = "[%s-%s-%s" %(str(flock.tm_year),str(flock.tm_mon),str(flock.tm_mday))
 
  if int(flock.tm_hour)<10:
    hrs = "0%s" % (str(flock.tm_hour))
  else:
    hrs = str(flock.tm_hour)
  if int(flock.tm_min)<10:
    mins = "0%s" % (str(flock.tm_min))
  else:
    mins = str(flock.tm_min)
 
  if int(flock.tm_sec)<10:
    secs = "0%s" % (str(flock.tm_sec))
  else:
    secs = str(flock.tm_sec)
 
  then +="]%s.%s.%s" % (hrs,mins,secs)
  return then
 
 
def _timer_func ():
  
  global intents, intents_phase
  routingController.update( intents )
  
  
  #---------------------------------------------------------------------------------------------------------------------
  # Funkcja wywolywana cyklicznie do wysylania wiadomosci pomiarowych do switchow
  global s1s2_start_time, s1s2_sent_time1, s1s2_sent_time2, s1s2_src_dpid, s1s2_dst_dpid
 
  # Wywolane tylko w momencie gdy jest polaczenie do switcha 0 istnieje
  if s1s2_src_dpid <>0 and not core.openflow.getConnection( s1s2_src_dpid ) is None:

    # Wyslanie pakietu port_status_request do pomiaru T1
    core.openflow.getConnection( s1s2_src_dpid ).send( of.ofp_stats_request( body=of.ofp_port_stats_request()) )
    s1s2_sent_time1=time.time() * 1000*10 - s1s2_start_time 

    # sekwencja operacji formatowania pakietu zoptymalizowana w celu zmniejszenia zmiennosci opoznienia pomiarow e-2-e (do pomiaru T3)
    f = myproto() #stworzenie pakietu probkujacego
    e = pkt.ethernet() #stworzenie ramki
    e.src = EthAddr( "10:20:00:00:00:00" )
    e.dst = EthAddr( "20:10:00:00:00:00" )
    e.type=0x5577 #ustawienie unregistered EtherType w naglowku L2
    msg = of.ofp_packet_out() #stworzenie wiadomosci PACKET_OUT
    msg.actions.append( of.ofp_action_output(port=4) ) #ustawienie portu wyjsciowego
    f.timestamp = int( time.time()*1000*10 - s1s2_start_time ) #ustawienie timestampa
    e.payload = f
    msg.data = e.pack()
    core.openflow.getConnection( s1s2_src_dpid ).send( msg )

  # Wywolane tylko w momencie gdy jest polaczenie do switcha 1 istnieje
  if s1s2_dst_dpid <>0 and not core.openflow.getConnection( s1s2_dst_dpid ) is None:
    # Wyslanie pakietu port_status_request do pomiaru T2
    core.openflow.getConnection( s1s2_dst_dpid ).send( of.ofp_stats_request(body=of.ofp_port_stats_request()) )
    s1s2_sent_time2=time.time() * 1000*10 - s1s2_start_time 
    
    
  #---------------------------------------------------------------------------------------------------------------------
  # Funkcja wywolywana cyklicznie do wysylania wiadomosci pomiarowych do switchow
  global s1s3_start_time, s1s3_sent_time1, s1s3_sent_time2, s1s3_src_dpid, s1s3_dst_dpid
 
  # Wywolane tylko w momencie gdy jest polaczenie do switcha 0 istnieje)
  if s1s3_src_dpid <>0 and not core.openflow.getConnection( s1s3_src_dpid ) is None:

    # Wyslanie pakietu port_status_request do pomiaru T1
    core.openflow.getConnection( s1s3_src_dpid ).send( of.ofp_stats_request(body=of.ofp_port_stats_request()) )
    s1s3_sent_time1=time.time() * 1000*10 - s1s3_start_time 

    # sekwencja operacji formatowania pakietu zoptymalizowana w celu zmniejszenia zmiennosci opoznienia pomiarow e-2-e (do pomiaru T3)
    f = myproto() #stworzenie pakietu probkujacego 
    e = pkt.ethernet() #stworzenie ramki
    e.src = EthAddr( "10:30:00:00:00:00" )
    e.dst = EthAddr( "30:10:00:00:00:00" )
    e.type=0x5578 #ustawienie unregistered EtherType w naglowku L2
    msg = of.ofp_packet_out() #stworzenie wiadomosci PACKET_OUT
    msg.actions.append( of.ofp_action_output(port=5) ) #ustawienie portu wyjsciowego
    f.timestamp = int( time.time()*1000*10 - s1s3_start_time ) #ustawienie timestampa
    e.payload = f
    msg.data = e.pack()
    core.openflow.getConnection( s1s3_src_dpid ).send( msg )

  # Wywolane tylko w momencie gdy jest polaczenie do switcha 1 istnieje)
  if s1s3_dst_dpid <>0 and not core.openflow.getConnection( s1s3_dst_dpid ) is None:
    # Wyslanie pakietu port_status_request do pomiaru T2
    core.openflow.getConnection( s1s3_dst_dpid ).send( of.ofp_stats_request(body=of.ofp_port_stats_request()) )
    s1s3_sent_time2=time.time() * 1000*10 - s1s3_start_time 
    
  #---------------------------------------------------------------------------------------------------------------------
  # Funkcja wywolywana cyklicznie do wysylania wiadomosci pomiarowych do switchow
  global s1s4_start_time, s1s4_sent_time1, s1s4_sent_time2, s1s4_src_dpid, s1s4_dst_dpid
 
  # Wywolane tylko w momencie gdy jest polaczenie do switcha 1 istnieje)
  if s1s4_src_dpid <>0 and not core.openflow.getConnection( s1s4_src_dpid ) is None:

    # Wyslanie pakietu port_status_request do pomiaru T1
    core.openflow.getConnection( s1s4_src_dpid ).send( of.ofp_stats_request(body=of.ofp_port_stats_request()) )
    s1s4_sent_time1=time.time() * 1000*10 - s1s4_start_time 

    # sekwencja operacji formatowania pakietu zoptymalizowana w celu zmniejszenia zmiennosci opoznienia pomiarow e-2-e (do pomiaru T3
    f = myproto() #stworzenie pakietu probkujacego
    e = pkt.ethernet() #stworzenie ramki
    e.src = EthAddr( "10:40:00:00:00:00" )
    e.dst = EthAddr( "40:10:00:00:00:00" )
    e.type=0x5579 #ustawienie unregistered EtherType w naglowku L2
    msg = of.ofp_packet_out() #stworzenie wiadomosci PACKET_OUT
    msg.actions.append( of.ofp_action_output(port=6) ) #ustawienie portu wyjsciowego
    f.timestamp = int( time.time()*1000*10 - s1s4_start_time ) #ustawienie timestampa
    e.payload = f
    msg.data = e.pack()
    core.openflow.getConnection( s1s4_src_dpid ).send( msg )

  # Wywolane tylko w momencie gdy jest polaczenie do switcha 1 istnieje)
  if s1s4_dst_dpid <>0 and not core.openflow.getConnection( s1s4_dst_dpid ) is None:
    # Wyslanie pakietu port_status_request do pomiaru T2
    core.openflow.getConnection( s1s4_dst_dpid ).send( of.ofp_stats_request(body=of.ofp_port_stats_request()) )
    s1s4_sent_time2=time.time() * 1000*10 - s1s4_start_time 
  

#--------Liczenie opoznienia na laczu miedzy kontrolerem i switchem w jedna strone--------
def _handle_portstats_received ( event ):

  global s1s2_start_time, s1s2_sent_time1, s1s2_sent_time2, s1s2_received_time1, s1s2_received_time2, s1s2_src_dpid, s1s2_dst_dpid, s1s2_OWD1, s1s2_OWD2

  s1s2_received_time = time.time() * 1000*10 - s1s2_start_time
  if event.connection.dpid == s1s2_src_dpid:
    s1s2_OWD1=0.5*( s1s2_received_time - s1s2_sent_time1 )
  elif event.connection.dpid == s1s2_dst_dpid:
    s1s2_OWD2=0.5*( s1s2_received_time - s1s2_sent_time2 ) 


  global s1s3_start_time, s1s3_sent_time1, s1s3_sent_time2, s1s3_received_time1, s1s3_received_time2, s1s3_src_dpid, s1s3_dst_dpid, s1s3_OWD1, s1s3_OWD2

  s1s3_received_time = time.time() * 1000*10 - s1s3_start_time
  if event.connection.dpid == s1s3_src_dpid:
    s1s3_OWD1=0.5*( s1s3_received_time - s1s3_sent_time1 )
  elif event.connection.dpid == s1s3_dst_dpid:
    s1s3_OWD2=0.5*( s1s3_received_time - s1s3_sent_time2 ) 


  global s1s4_start_time, s1s4_sent_time1, s1s4_sent_time2, s1s4_received_time1, s1s4_received_time2, s1s4_src_dpid, s1s4_dst_dpid, s1s4_OWD1, s1s4_OWD2

  s1s4_received_time = time.time() * 1000*10 - s1s4_start_time
  if event.connection.dpid == s1s4_src_dpid:
    s1s4_OWD1=0.5*( s1s4_received_time - s1s4_sent_time1 )
  elif event.connection.dpid == s1s4_dst_dpid:
    s1s4_OWD2=0.5*( s1s4_received_time - s1s4_sent_time2 ) 


    
#Obsluga podlaczenia sie switcha do kontrolera
def _handle_ConnectionUp ( event ):
  global s1_dpid, s2_dpid, s3_dpid, s4_dpid, s5_dpid, s1s2_dst_dpid, s1s2_src_dpid, s1s3_dst_dpid, s1s3_src_dpid, s1s4_dst_dpid, s1s4_src_dpid
  print "ConnectionUp: ",dpidToStr( event.connection.dpid )
 
  for m in event.connection.features.ports:
    if m.name == "s1-eth1":
      s1_dpid = event.connection.dpid
      print "s1_dpid=", s1_dpid
    elif m.name == "s2-eth1":
      s2_dpid = event.connection.dpid
      s1s2_dst_dpid = event.connection.dpid
      print "s2_dpid=", s2_dpid
      print "s1s2_dst_dpid=", s1s2_dst_dpid
    elif m.name == "s3-eth1":
      s3_dpid = event.connection.dpid
      s1s3_dst_dpid = event.connection.dpid
      print "s3_dpid=", s3_dpid
      print "s1s3_dst_dpid=", s1s3_dst_dpid
    elif m.name == "s4-eth1":
      s4_dpid = event.connection.dpid
      s1s4_dst_dpid = event.connection.dpid
      print "s4_dpid=", s4_dpid
      print "s1s4_dst_dpid=", s1s4_dst_dpid
    elif m.name == "s5-eth1":
      s5_dpid = event.connection.dpid
      print "s5_dpid=", s5_dpid


    elif m.name == "s1-eth4":
      s1s2_src_dpid = event.connection.dpid
      print "s1s2_src_dpid=", s1s2_src_dpid
    elif m.name == "s1-eth5":
      s1s3_src_dpid = event.connection.dpid
      print "s1s3_src_dpid=", s1s3_src_dpid
    elif m.name == "s1-eth6":
      s1s4_src_dpid = event.connection.dpid
      print "s1s4_src_dpid=", s1s4_src_dpid
 
  if s1_dpid<>0 and s2_dpid<>0 and s3_dpid<>0 and s4_dpid<>0 and s5_dpid<>0:
    Timer( 3, _timer_func, recurring=True )

#Obsluga pakietow przychodzacych 
def _handle_PacketIn( event ):
  global s1_dpid, s2_dpid, s3_dpid, s4_dpid, s5_dpid
 
  packet=event.parsed


  #--------Liczenie opoznienia na laczach--------
  global s1s2_start_time, s1s2_OWD1, s1s2_OWD2, s1s2_delay

  s1s2_received_time = time.time() * 1000*10 - s1s2_start_time #czas ktory uplynal od start_time
 
  if packet.type==0x5577 and event.connection.dpid==s1s2_dst_dpid: #0x5577 unregistered EtherType, w przypisany do pakietow probkujacych
    # Przetwarzanie pakietu probkujacego odczymanego w wiadomosci PACKET_IN od switcha 1 (dst_dpid), wczesniej wyslany do switcha 0 PACKET_OUT

    c=packet.find( 'ethernet' ).payload
    d,=struct.unpack( '!I', c ) 
    s1s2_delay = int( s1s2_received_time - d - s1s2_OWD1 - s1s2_OWD2 )/10

  #---------------------------------------------------------------------------------------------------------------------
  global s1s3_start_time, s1s3_OWD1, s1s3_OWD2, s1s3_delay

  s1s3_received_time = time.time() * 1000*10 - s1s3_start_time #czas ktory uplynal od start time
 
  if packet.type==0x5578 and event.connection.dpid==s1s3_dst_dpid: #0x5577 unregistered EtherType, w przypisany do pakietow probkujacych
    # Przetwarzanie pakietu probkujacego odczymanego w wiadomosci PACKET_IN od switcha 1 (dst_dpid), wczesniej wyslany do switcha 0 PACKET_OUT

    c=packet.find( 'ethernet' ).payload
    d,=struct.unpack( '!I', c )
    s1s3_delay = int( s1s3_received_time - d - s1s3_OWD1 - s1s3_OWD2 )/10
  
  #---------------------------------------------------------------------------------------------------------------------
  global s1s4_start_time, s1s4_OWD1, s1s4_OWD2, s1s4_delay

  s1s4_received_time = time.time() * 1000*10 - s1s4_start_time #czas ktory uplynal od start_time
 
  if packet.type==0x5579 and event.connection.dpid==s1s4_dst_dpid: #0x5577 unregistered EtherType, w przypisany do pakietow probkujacych
    # Przetwarzanie pakietu probkujacego odczymanego w wiadomosci PACKET_IN od switcha 1 (dst_dpid), wczesniej wyslany do switcha 0 PACKET_OUT

    c=packet.find( 'ethernet' ).payload
    d,=struct.unpack( '!I', c )  
    s1s4_delay = int( s1s4_received_time - d - s1s4_OWD1 - s1s4_OWD2 )/10

  #ustawianie domyslnego routingu 
  if event.connection.dpid==s1_dpid or event.connection.dpid==s5_dpid:
    a=packet.find( 'arp' )					
    routing_table = { 
       "10.0.0.1": 1,
       "10.0.0.2": 2,
       "10.0.0.3": 3,
       "10.0.0.4": 4,
       "10.0.0.5": 5,
       "10.0.0.6": 6
     }
    if a: 
      msg = of.ofp_packet_out( data=event.ofp )			
      msg.actions.append( of.ofp_action_output(port = routing_table[str(a.protodst)]) )		
      event.connection.send( msg )				

    for _, ( ip_add, port ) in enumerate( routing_table.items() ):
      msg = of.ofp_flow_mod()
      msg.priority =100
      msg.idle_timeout = 0
      msg.hard_timeout = 0
      msg.match.dl_type = 0x0800		# rule for IP packets (x0800)
      msg.match.nw_dst = str( ip_add )
      msg.actions.append( of.ofp_action_output(port = int(port)) )
      event.connection.send( msg )
    
  elif event.connection.dpid==s2_dpid or event.connection.dpid==s3_dpid or event.connection.dpid==s4_dpid:
    match_table = [( 1, 0x0806, 2 ), ( 1, 0x0800, 2 ), ( 2, 0x0806, 1 ), ( 2, 0x0800, 1 )]
    for _, ( in_port, dl_type, port ) in enumerate( match_table ):
      msg = of.ofp_flow_mod()
      msg.priority =10
      msg.idle_timeout = 0
      msg.hard_timeout = 0
      msg.match.in_port = in_port
      msg.match.dl_type= dl_type		# rule for ARP packets (x0806)
      msg.actions.append( of.ofp_action_output(port = port) )
      event.connection.send( msg )



#Inicializacja intentow
intent1 = Intent( "h2", "10.0.0.6", 100, 110 )
intent2 = Intent( "h1", "10.0.0.4", 20, 100 )
intent3 = Intent( "h3", "10.0.0.6", 10, 113 )
intent4 = Intent( "h1", "10.0.0.5", 60, 101 )
intent5 = Intent( "h1", "10.0.0.5", 40, 104 )
intent6 = Intent( "h2", "10.0.0.5", 200, 102 )
intent7 = Intent( "h3", "10.0.0.6", 50, 109 )
intent8 = Intent( "h3", "10.0.0.4", 100, 119 )

intents = [intent1, intent2, intent3, intent4, intent5, intent6, intent7, intent8 ]


routingController = RoutingController()
intents.sort()
print "RoutingController: Intends sorted"

# As usually, launch() is the function called by POX to initialize the component (routing_controller.py in our case) 
# indicated by a parameter provided to pox.py 

def launch ():
  # Ustawienie poczatkowego czasu
  global s1s2_start_time, s1s3_start_time, s1s4_start_time
  s1s2_start_time = time.time() * 1000*10
  s1s3_start_time = s1s2_start_time
  s1s4_start_time = s1s2_start_time
  # core is an instance of class POXCore (EventMixin) and it can register objects.
  # An object with name xxx can be registered to core instance which makes this object become a "component" available as pox.core.core.xxx.
  # for examples see e.g. https://noxrepo.github.io/pox-doc/html/#the-openflow-nexus-core-openflow 
  core.openflow.addListenerByName( "PortStatsReceived",_handle_portstats_received ) # listen for port stats , https://noxrepo.github.io/pox-doc/html/#statistics-events
  core.openflow.addListenerByName( "ConnectionUp", _handle_ConnectionUp ) # listen for the establishment of a new control channel with a switch, https://noxrepo.github.io/pox-doc/html/#connectionup
  core.openflow.addListenerByName( "PacketIn",_handle_PacketIn ) # listen for the reception of packet_in message from switch, https://noxrepo.github.io/pox-doc/html/#packetin
