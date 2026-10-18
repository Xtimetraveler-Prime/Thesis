# P07-A2 only: stage immutable frozen DDR, versioned ingress records and
# batch descriptor. NEVER use P05G/accepted P05 diagnostic payload here.
# Prepare only; does not start A53 or issue PL dispatch.
if {$argc < 3 || $argc > 4} {
    error "usage: p07_a2_xsdb_prepare.tcl <static-ddr-512k> <p07-a2-batch-dir> <readback-dir> ?server?"
}
set master [file normalize [lindex $argv 0]]
set batch [file normalize [lindex $argv 1]]
set out [file normalize [lindex $argv 2]]
set server "tcp:127.0.0.1:3121"
if {$argc == 4} {set server [lindex $argv 3]}
set header [file join $batch p07_a2_header_64.bin]
set payload [file join $batch p07_a2_ingress_payload.bin]
set mailbox [file join $batch p07_a2_mailbox_zero_64k.bin]
if {![file exists $master] || [file size $master] != 524288} {
    error "P07-A2 immutable P02 master must be exactly 512KiB"
}
set sha [lindex [exec sha256sum $master] 0]
if {$sha ne "9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955"} {
    error "P07-A2 master DDR differs from user-accepted P06-A4 hash"
}
if {![file exists $header] || [file size $header] != 64 ||
    ![file exists $payload] || [file size $payload] < 2480 ||
    [file size $payload] > 39680 || [file size $payload] % 2480 != 0 ||
    ![file exists $mailbox] || [file size $mailbox] != 65536} {
    error "P07-A2 batch files/lengths invalid"
}
file mkdir $out
proc select_physical {} {
    foreach name {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$name\""}]} {
            puts "P07-A2 selected physical target: $name"
            return
        }
    }
    error "P07-A2 PSU/APU target unavailable"
}
proc equal_binary {left right} {
    set a [open $left rb]; set b [open $right rb]
    fconfigure $a -translation binary -encoding binary
    fconfigure $b -translation binary -encoding binary
    set pass [expr {[read $a] eq [read $b]}]
    close $a;close $b
    return $pass
}
connect -url $server
targets -set -filter {name =~ "Cortex-A53 #0"}
catch {stop}
select_physical
foreach item [list \
    [list $master 0x43F00000] \
    [list $payload 0x43F80000] \
    [list $header 0x43FE0000] \
    [list $mailbox 0x43FF0000]] {
    lassign $item data address
    set size [file size $data]
    set dump [file join $out [format "readback_%08X.bin" $address]]
    file delete -force $dump
    puts [format "P07-A2 staging 0x%08X (%d bytes)" $address $size]
    dow -data $data $address
    mrd -bin -file $dump $address [expr {$size/4}]
    if {![equal_binary $data $dump]} {
        error "P07-A2 byte-precise physical DDR staging readback mismatch"
    }
}
puts "P07_A2_XSDB_PROVISION_PASS=1"
puts "P07_A2_KV260_INFERENCE=NOT_RUN"
disconnect
